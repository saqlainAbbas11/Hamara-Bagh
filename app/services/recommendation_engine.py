"""
The core original logic of this project: no free API maps "climate at this
location" to "plants suited to it". We build that mapping ourselves by
scoring every plant in our dataset against a live climate snapshot.
"""
from app.models import Plant

HUMIDITY_RANK = {"very_low": 0, "low": 1, "medium": 2, "high": 3}


def classify_zone(snapshot: dict) -> dict:
    """Turn a raw weather snapshot into a human-friendly climate zone label.
    Deliberately simple thresholds - good enough to guide plant selection,
    not a real Koppen classification.
    """
    avg_max = snapshot["avg_max_temp_c"]
    avg_min = snapshot["avg_min_temp_c"]
    precip = snapshot["total_precip_mm_16d"]
    humidity = snapshot.get("avg_humidity_pct")

    if avg_max >= 38:
        heat = "extreme_heat"
    elif avg_max >= 32:
        heat = "hot"
    elif avg_max >= 24:
        heat = "warm"
    elif avg_max >= 15:
        heat = "mild"
    else:
        heat = "cool"

    if precip >= 60:
        moisture = "wet"
    elif precip >= 15:
        moisture = "moderate_rain"
    else:
        moisture = "dry"

    if humidity is not None:
        if humidity >= 65:
            humidity_label = "humid"
        elif humidity >= 35:
            humidity_label = "moderate_humidity"
        else:
            humidity_label = "arid"
    else:
        humidity_label = "unknown"

    label = f"{heat}, {moisture}, {humidity_label}"
    frost_risk = avg_min <= 2

    return {
        "heat": heat,
        "moisture": moisture,
        "humidity_label": humidity_label,
        "frost_risk": frost_risk,
        "label": label,
    }


# ---------------------------------------------------------------------------
# Indoor / window-sill mode
# ---------------------------------------------------------------------------
# Buildings dampen outdoor extremes: cold nights stay warmer and midday peaks
# stay lower. These deltas are deliberately simple heuristics - honest enough
# that the engine stops judging a houseplant on a garden frost it will never
# feel on a windowsill.
INDOOR_NIGHT_GAIN_C = 6.0      # coldest nights are buffered by the building
INDOOR_DAY_SHADE_C = 6.0       # midday peaks are cut by walls, roofs and shade
INDOOR_MIN_SPREAD_C = 4.0      # keep a sane range for very mild climates
INDOOR_PRECIP_MM = 0.0         # rain never reaches an indoor plant; the water factor is neutralized in score_plant
INDOOR_NEUTRAL_HUMIDITY_PCT = 45.0


def apply_indoor_profile(snapshot: dict) -> dict:
    """Return an indoor-adjusted copy of an outdoor climate snapshot.

    Temperatures are compressed toward room conditions (+6 on the cold side
    including the forecast low, -6 on the hot side including the peak),
    humidity is pulled halfway toward a typical indoor 45%, and
    precipitation is zeroed because rainfall never reaches an indoor plant
    (score_plant neutralizes the water factor in indoor mode).
    "now" temperature keeps its offset but is clamped inside the adjusted
    range.
    """
    adjusted = dict(snapshot)

    new_min = snapshot["avg_min_temp_c"] + INDOOR_NIGHT_GAIN_C
    new_max = snapshot["avg_max_temp_c"] - INDOOR_DAY_SHADE_C
    if new_max - new_min < INDOOR_MIN_SPREAD_C:
        new_max = new_min + INDOOR_MIN_SPREAD_C

    new_lowest = snapshot.get("lowest_min_temp_c")
    if new_lowest is not None:
        new_lowest += INDOOR_NIGHT_GAIN_C
        adjusted["lowest_min_temp_c"] = round(new_lowest, 1)

    new_peak = snapshot.get("peak_max_temp_c")
    if new_peak is not None:
        new_peak -= INDOOR_DAY_SHADE_C
        new_peak = max(new_peak, new_max)
        adjusted["peak_max_temp_c"] = round(new_peak, 1)

    adjusted["avg_min_temp_c"] = round(new_min, 1)
    adjusted["avg_max_temp_c"] = round(new_max, 1)

    current = snapshot.get("current_temp_c")
    if current is not None:
        adjusted["current_temp_c"] = round(min(max(current + INDOOR_NIGHT_GAIN_C, new_min), new_max), 1)

    humidity = snapshot.get("avg_humidity_pct")
    if humidity is not None:
        adjusted["avg_humidity_pct"] = round(
            INDOOR_NEUTRAL_HUMIDITY_PCT + (humidity - INDOOR_NEUTRAL_HUMIDITY_PCT) * 0.5, 1
        )

    adjusted["total_precip_mm_16d"] = INDOOR_PRECIP_MM
    return adjusted


def _temp_fit_score(plant: Plant, snapshot: dict) -> float:
    """0-40 points based on how well the forecast temperature range sits
    inside the plant's ideal range, with graceful falloff outside it."""
    avg_max = snapshot["avg_max_temp_c"]
    avg_min = snapshot["avg_min_temp_c"]
    peak_max = snapshot["peak_max_temp_c"]
    lowest_min = snapshot["lowest_min_temp_c"]

    if plant.ideal_temp_min_c is None or plant.ideal_temp_max_c is None:
        return 20  # neutral if data missing

    score = 40.0

    # Ideal range overlap bonus
    if plant.ideal_temp_min_c <= avg_max <= plant.ideal_temp_max_c and \
       plant.ideal_temp_min_c <= avg_min <= plant.ideal_temp_max_c:
        score = 40.0
    else:
        # penalize distance outside the ideal range
        over = max(0, avg_max - plant.ideal_temp_max_c)
        under = max(0, plant.ideal_temp_min_c - avg_min)
        score -= (over + under) * 2.5

    # Hard survivability check: forecast peak/lowest outside absolute min/max
    if plant.max_temp_c is not None and peak_max > plant.max_temp_c:
        score -= (peak_max - plant.max_temp_c) * 4
    if plant.min_temp_c is not None and lowest_min < plant.min_temp_c:
        score -= (plant.min_temp_c - lowest_min) * 4

    return max(0.0, min(40.0, score))


def _water_fit_score(plant: Plant, snapshot: dict) -> float:
    """0-25 points - rewards low-water plants in dry climates and doesn't
    punish high-water plants too harshly (since irrigation/manual watering
    can compensate - unlike temperature, which the plant just has to endure).
    """
    precip = snapshot["total_precip_mm_16d"]
    water_need = plant.water_need or "medium"

    is_dry_climate = precip < 15

    if not is_dry_climate:
        return 25.0  # rainfall is adequate, watering need matters less here

    # dry climate: reward drought tolerance
    dry_climate_scores = {"very_low": 25, "low": 20, "medium": 12, "high": 4}
    return dry_climate_scores.get(water_need, 12)


def _humidity_fit_score(plant: Plant, snapshot: dict) -> float:
    """0-15 points based on humidity preference alignment."""
    humidity = snapshot.get("avg_humidity_pct")
    if humidity is None or not plant.humidity_pref:
        return 10  # neutral

    plant_rank = HUMIDITY_RANK.get(plant.humidity_pref, 2)
    if humidity >= 65:
        actual_rank = 3
    elif humidity >= 35:
        actual_rank = 2
    else:
        actual_rank = 1

    diff = abs(plant_rank - actual_rank)
    return max(0.0, 15 - diff * 6)


def _season_fit_score(plant: Plant, current_month: int) -> float:
    """0-10 bonus points if right now is actually a good sowing month."""
    if plant.season == "perennial":
        return 6  # always plantable, moderate bonus
    if current_month in (plant.sow_months or []):
        return 10
    return 0


def _difficulty_bonus(plant: Plant, beginner_mode: bool) -> float:
    """0-10 bonus for easy plants when the user wants beginner-friendly results."""
    if not beginner_mode:
        return 5
    bonus_map = {"very_easy": 10, "easy": 7, "medium": 3, "hard": 0}
    return bonus_map.get(plant.difficulty, 3)


def score_plant(plant: Plant, snapshot: dict, current_month: int, beginner_mode: bool = True,
                 air_quality: dict = None, indoor: bool = False) -> dict:
    temp_score = _temp_fit_score(plant, snapshot)
    # Indoors, rainfall is irrelevant and watering is fully manual - the water
    # factor must neither reward nor penalize, so it stays neutral.
    water_score = 25.0 if indoor else _water_fit_score(plant, snapshot)
    humidity_score = _humidity_fit_score(plant, snapshot)
    season_score = _season_fit_score(plant, current_month)
    difficulty_score = _difficulty_bonus(plant, beginner_mode)

    total = temp_score + water_score + humidity_score + season_score + difficulty_score

    # Air quality adjustment: small penalty for pollution-sensitive plants
    # in genuinely bad air, small bonus for pollution-tolerant ones
    aqi_note = None
    aqi_key = None
    if air_quality and air_quality.get("level") in ("unhealthy", "unhealthy_for_sensitive_groups"):
        if plant.pollution_tolerant:
            total += 3
            aqi_note = "Bonus: tolerates poor air quality, relevant for your current air conditions."
            aqi_key = "reason_aqi_bonus"
        else:
            total -= 5
            aqi_note = "Caution: local air quality is currently poor and this plant is not known to be pollution tolerant."
            aqi_key = "reason_aqi_caution"

    total = max(0.0, min(100.0, total))

    if total >= 75:
        verdict = "excellent_match"
    elif total >= 55:
        verdict = "good_match"
    elif total >= 35:
        verdict = "risky"
    else:
        verdict = "not_recommended"

    reasons = []
    reason_keys = []
    if temp_score >= 32:
        reasons.append("Temperature range matches well.")
        reason_keys.append("reason_temp_good")
    elif temp_score <= 15:
        reasons.append("Temperature is a significant mismatch for this plant.")
        reason_keys.append("reason_temp_bad")
    if not indoor and water_score >= 20:
        reasons.append("Well suited to current rainfall/dryness.")
        reason_keys.append("reason_water_good")
    elif not indoor and water_score <= 8:
        reasons.append("Will likely need frequent manual watering here.")
        reason_keys.append("reason_water_needs_irrigation")
    if season_score == 10:
        reasons.append("Right now is a good sowing month for this plant.")
        reason_keys.append("reason_season_good")
    elif season_score == 0 and plant.season != "perennial":
        reasons.append("This isn't the ideal sowing season - consider waiting.")
        reason_keys.append("reason_season_not_ideal")
    if aqi_note:
        reasons.append(aqi_note)
    if aqi_key:
        reason_keys.append(aqi_key)

    return {
        "plant": plant.to_dict(),
        "score": round(total, 1),
        "verdict": verdict,
        "breakdown": {
            "temperature": round(temp_score, 1),
            "water": round(water_score, 1),
            "humidity": round(humidity_score, 1),
            "season_timing": round(season_score, 1),
            "difficulty_bonus": round(difficulty_score, 1),
        },
        "reasons": reasons,
        "reason_keys": reason_keys,
    }


def recommend_plants(snapshot: dict, current_month: int, beginner_mode: bool = True,
                      category: str = None, air_quality: dict = None, limit: int = 12,
                      indoor: bool = False):
    query = Plant.query
    if category:
        query = query.filter(Plant.category == category)

    plants = query.all()
    scored = [score_plant(p, snapshot, current_month, beginner_mode, air_quality, indoor) for p in plants]
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:limit]
