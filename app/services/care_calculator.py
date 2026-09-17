"""
Turns a plant's static water_need label into a concrete "water every N days"
estimate, adjusted for the current/forecast temperature - because "medium
water" means something very different at 45C in Multan than at 22C in Murree.

If plant is None (e.g. a journal entry saved without a species), the
estimate falls back to a generic "medium" need.
"""

BASE_INTERVAL_DAYS = {
    "very_low": 18,
    "low": 10,
    "medium": 5,
    "high": 2,
}


def estimate_watering_interval(plant, snapshot: dict = None):
    water_need = getattr(plant, "water_need", None) or "medium"
    base = BASE_INTERVAL_DAYS.get(water_need, 5)

    if not snapshot:
        return {
            "interval_days": base,
            "note": "Based on general care guidelines only (no local climate data supplied).",
        }

    avg_max = snapshot.get("avg_max_temp_c")
    humidity = snapshot.get("avg_humidity_pct")

    multiplier = 1.0
    notes = []

    if avg_max is not None:
        if avg_max >= 38:
            multiplier *= 0.55
            notes.append("extreme heat is speeding up soil drying significantly")
        elif avg_max >= 32:
            multiplier *= 0.7
            notes.append("hot conditions are drying soil faster than average")
        elif avg_max <= 15:
            multiplier *= 1.4
            notes.append("cool weather is slowing evaporation, water less often")

    if humidity is not None:
        if humidity <= 30:
            multiplier *= 0.85
            notes.append("low humidity increases water loss")
        elif humidity >= 70:
            multiplier *= 1.15
            notes.append("high humidity reduces how fast soil dries")

    adjusted = max(1, round(base * multiplier))

    return {
        "interval_days": adjusted,
        "base_interval_days": base,
        "note": ("Adjusted for current conditions: " + "; ".join(notes)) if notes else
                "Based on general care guidelines (no strong adjustment needed for current conditions).",
    }
