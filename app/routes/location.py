from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Plant
from app.services import care_calculator, i18n, recommendation_engine, seasonal_calendar, weather_service
from app.utils import int_arg

bp = Blueprint("location", __name__, url_prefix="/api/location")


def _resolve_coordinates(prefix=""):
    """Support ?city=Karachi or ?lat=..&lon=.. directly (the optional prefix
    'a_' / 'b_' is used by /compare). Both spellings are accepted -
    ?a_city=... and ?city_a=... - because the /compare docs and UI use the
    suffix style (?city_a=Karachi&city_b=Islamabad). Never raises - returns
    a clean error dict so a flaky connection degrades gracefully instead of
    crashing.
    """

    def _arg(base):
        """Look up a query param by prefix-first (a_city) or suffix (city_a)
        spelling, returning whichever is present."""
        names = [f"{prefix}{base}"]
        if prefix:
            names.append(f"{base}_{prefix.rstrip('_')}")
        for name in names:
            if name in request.args:
                return request.args.get(name)
        return None

    lat_raw, lon_raw = _arg("lat"), _arg("lon")
    if lat_raw is not None and lon_raw is not None:
        try:
            return float(lat_raw), float(lon_raw), None, None
        except (TypeError, ValueError):
            return None, None, None, {
                "error": f"Coordinates must be numbers, e.g. ?{prefix}lat=24.86&{prefix}lon=67.00"
            }

    city = _arg("city")
    if not city:
        return None, None, None, {
            "error": f"Provide either ?{prefix}city=NAME or ?{prefix}lat=..&{prefix}lon=.."
        }

    geo = weather_service.geocode_city(city)
    if geo and geo.get("network_error"):
        return None, None, None, {"error": "Could not reach the weather/geocoding service right now. "
                                           "Check your internet connection and try again."}
    if not geo or not geo.get("found"):
        return None, None, None, {"error": f"Could not find a location matching '{city}'."}

    city_name = f"{geo.get('name')}, {geo.get('country')}"
    return geo["lat"], geo["lon"], city_name, None


def _localized_zone(zone, lang):
    if lang == "en":
        return zone
    localized = dict(zone)
    localized["label_localized"] = ", ".join([
        i18n.t(f"zone.heat.{zone['heat']}", lang),
        i18n.t(f"zone.moisture.{zone['moisture']}", lang),
        i18n.t(f"zone.humidity.{zone['humidity_label']}", lang),
    ])
    return localized


def _localized_season(season_info, lang):
    if lang == "en":
        return season_info
    return {
        **season_info,
        "label_localized": i18n.t(f"season.{season_info['season']}.label", lang),
        "description_localized": i18n.t(f"season.{season_info['season']}.description", lang),
    }


def _localize_scored_result(result, lang):
    """Add a localized verdict label + reasons alongside the machine-readable
    fields. reason_keys (emitted by the engine) drive the translation."""
    result["verdict_label"] = i18n.t(f"verdict.{result['verdict']}", lang)
    reason_keys = result.get("reason_keys") or []
    if reason_keys:
        result["reasons"] = [i18n.t(key, lang) for key in reason_keys]
    return result


def _apply_indoor_reasons(result):
    """Indoor mode neutralizes the rainfall factor (watering is fully
    manual), so swap the generic water reason for a mode explainer."""
    keys = [k for k in result.get("reason_keys") or [] if k != "reason_water_good"]
    keys.append("reason_indoor_mode")
    result["reason_keys"] = keys


def _score_one_plant(plant_id, lat, lon, lang, air_quality=None, indoor=False):
    """Score a single plant against one location - shared by /compare.
    Returns (payload, error_response_or_None).
    """
    plant = db.session.get(Plant, plant_id)
    if plant is None:
        return None, (jsonify({"error": f"No plant with id {plant_id}"}), 404)

    snapshot = weather_service.get_climate_snapshot(lat, lon)
    if not snapshot:
        return None, (jsonify({"error": "Weather data unavailable for this location right now."}), 502)

    if indoor:
        snapshot = recommendation_engine.apply_indoor_profile(snapshot)

    zone = recommendation_engine.classify_zone(snapshot)
    result = recommendation_engine.score_plant(plant, snapshot, datetime.now().month, air_quality=air_quality, indoor=indoor)
    result["watering"] = care_calculator.estimate_watering_interval(plant, snapshot)
    if indoor:
        _apply_indoor_reasons(result)
    _localize_scored_result(result, lang)

    return {"snapshot": snapshot, "zone": zone, "result": result}, None


@bp.route("/climate", methods=["GET"])
def climate():
    """Raw climate snapshot + zone classification for a city or lat/lon."""
    lat, lon, city_name, err = _resolve_coordinates()
    if err:
        return jsonify(err), 400

    snapshot = weather_service.get_climate_snapshot(lat, lon)
    if not snapshot:
        return jsonify({"error": "Weather data unavailable for this location right now."}), 502

    zone = recommendation_engine.classify_zone(snapshot)
    return jsonify({"location": {"lat": lat, "lon": lon, "resolved_name": city_name},
                     "snapshot": snapshot, "zone": zone})


@bp.route("/recommend", methods=["GET"])
def recommend():
    """The main feature: given a location, return scored/ranked plant
    recommendations. Query params:
      city=Karachi  OR  lat=..&lon=..
      category=vegetable|herb|flower|tree|succulent|houseplant
      beginner=1  (default true) - weights easy plants higher
      indoor=1    - score as indoor / window-sill conditions (buffered
                    temperatures, rainfall ignored, air quality not scored)
      limit=12    (clamped to 1-50)
      month=1-12  (defaults to the current month)
      lang=en|ur  (localized verdict/reasons/zone/season)
    """
    lat, lon, city_name, err = _resolve_coordinates()
    if err:
        return jsonify(err), 400

    indoor = request.args.get("indoor", "0") == "1"

    snapshot = weather_service.get_climate_snapshot(lat, lon)
    if not snapshot:
        return jsonify({"error": "Weather data unavailable for this location right now."}), 502

    if indoor:
        snapshot = recommendation_engine.apply_indoor_profile(snapshot)

    zone = recommendation_engine.classify_zone(snapshot)

    air_quality = None
    if not indoor:
        try:
            air_quality = weather_service.get_air_quality(lat, lon)
        except Exception:  # noqa: BLE001 - air quality is a bonus signal, never block on it
            pass

    category = request.args.get("category")
    beginner_mode = request.args.get("beginner", "1") != "0"
    limit = int_arg("limit", 12, minimum=1, maximum=50)
    month = int_arg("month", datetime.now().month, minimum=1, maximum=12)
    lang = i18n.resolve_lang()

    results = recommendation_engine.recommend_plants(
        snapshot, month, beginner_mode=beginner_mode,
        category=category, air_quality=air_quality, limit=limit, indoor=indoor,
    )

    # Attach per-plant watering estimates with one batched query - the old
    # per-result Plant.query.get() was an N+1 and used a deprecated API.
    plant_ids = [r["plant"]["id"] for r in results]
    plant_map = {}
    if plant_ids:
        rows = db.session.query(Plant).filter(Plant.id.in_(plant_ids)).all()
        plant_map = {p.id: p for p in rows}
    for r in results:
        plant_obj = plant_map.get(r["plant"]["id"])
        if plant_obj is not None:
            r["watering"] = care_calculator.estimate_watering_interval(plant_obj, snapshot)
        if indoor:
            _apply_indoor_reasons(r)
        _localize_scored_result(r, lang)

    season_info = _localized_season(seasonal_calendar.current_agri_season(month), lang)

    return jsonify({
        "lang": lang,
        "indoor": indoor,
        "location": {"lat": lat, "lon": lon, "resolved_name": city_name},
        "snapshot": snapshot,
        "zone": _localized_zone(zone, lang),
        "air_quality": air_quality,
        "agri_season": season_info,
        "results": results,
    })


@bp.route("/compare", methods=["GET"])
def compare():
    """Side-by-side verdict for one plant in two locations
    (e.g. Karachi vs Islamabad for the same lemon tree).
    Query: ?plant_id=1&city_a=Karachi&city_b=Islamabad
       or: ?plant_id=1&lat_a=..&lon_a=..&lat_b=..&lon_b=..
       optional &indoor=1 to score both locations as indoor / window-sill
    """
    plant_id = request.args.get("plant_id", type=int)
    if not plant_id:
        return jsonify({"error": "Provide ?plant_id="}), 400

    lat_a, lon_a, name_a, err_a = _resolve_coordinates("a_")
    if err_a:
        return jsonify({"error": f"Location A: {err_a['error']}"}), 400
    lat_b, lon_b, name_b, err_b = _resolve_coordinates("b_")
    if err_b:
        return jsonify({"error": f"Location B: {err_b['error']}"}), 400

    lang = i18n.resolve_lang()
    indoor = request.args.get("indoor", "0") == "1"

    air_a = air_b = None
    if not indoor:
        try:
            air_a = weather_service.get_air_quality(lat_a, lon_a)
        except Exception:  # noqa: BLE001
            pass
        try:
            air_b = weather_service.get_air_quality(lat_b, lon_b)
        except Exception:  # noqa: BLE001
            pass

    side_a, err = _score_one_plant(plant_id, lat_a, lon_a, lang, air_a, indoor)
    if err:
        return err
    side_b, err = _score_one_plant(plant_id, lat_b, lon_b, lang, air_b, indoor)
    if err:
        return err

    score_a = side_a["result"]["score"]
    score_b = side_b["result"]["score"]
    if abs(score_a - score_b) < 3:
        better = "tie"
        comparison = "Both locations are roughly equally suitable for this plant."
    elif score_a > score_b:
        better = "a"
        comparison = f"Clearly better in {name_a or 'location A'}."
    else:
        better = "b"
        comparison = f"Clearly better in {name_b or 'location B'}."

    return jsonify({
        "lang": lang,
        "indoor": indoor,
        "plant": side_a["result"]["plant"],
        "a": {"location": {"lat": lat_a, "lon": lon_a, "resolved_name": name_a},
              "air_quality": air_a, **side_a},
        "b": {"location": {"lat": lat_b, "lon": lon_b, "resolved_name": name_b},
              "air_quality": air_b, **side_b},
        "better_location": better,
        "comparison": comparison,
    })


@bp.route("/hardiness", methods=["GET"])
def hardiness():
    """How cold does it actually get here? An approximate hardiness profile
    from 5 years of historical daily data - the closest free equivalent to a
    USDA hardiness zone, which doesn't exist publicly for Pakistan (a full
    zone *map* is on the README roadmap).
    """
    lat, lon, city_name, err = _resolve_coordinates()
    if err:
        return jsonify(err), 400

    profile = weather_service.get_hardiness_profile(lat, lon)
    if not profile:
        return jsonify({"error": "Historical climate data unavailable for this location right now."}), 502

    return jsonify({"location": {"lat": lat, "lon": lon, "resolved_name": city_name},
                    "hardiness": profile})


@bp.route("/seasonal-calendar", methods=["GET"])
def seasonal_calendar_route():
    """What's good to sow right now, independent of specific location.
    Query params: month=1-12 (defaults to the current month), lang=en|ur
    """
    month = int_arg("month", datetime.now().month, minimum=1, maximum=12)
    lang = i18n.resolve_lang()
    season_info = _localized_season(seasonal_calendar.current_agri_season(month), lang)
    plants = seasonal_calendar.what_to_sow_now(month)
    return jsonify({"month": month, "season": season_info, "plants_to_sow": plants, "lang": lang})


@bp.route("/reference-cities", methods=["GET"])
def reference_cities():
    """Static reference climate data for major Pakistani cities - useful
    for a quick-pick dropdown in the UI without needing a live API call.
    """
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "city_climate_reference.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


def _pretty_city_name(slug):
    """'dera_ismail_khan' -> 'Dera Ismail Khan'."""
    return " ".join(part.capitalize() for part in slug.split("_"))


def _load_city_guides():
    """Flatten data/city_growing_guides.json (province -> cities) into
    ({city_slug: guide}, [province_info, ...]). Each city gains the keys
    'province' and 'province_name'; province_info keeps display order,
    English + Urdu names and the city count for the /guides filter UI.
    """
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "city_growing_guides.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cities, provinces = {}, []
    for prov_slug, body in data.get("provinces", {}).items():
        provinces.append({
            "slug": prov_slug,
            "name": body.get("name", prov_slug),
            "name_ur": body.get("name_ur", ""),
            "city_count": len(body.get("cities", {})),
        })
        for city_slug, guide in body.get("cities", {}).items():
            enriched = dict(guide)
            enriched["province"] = prov_slug
            enriched["province_name"] = body.get("name", prov_slug)
            cities[city_slug] = enriched
    return cities, provinces


def _match_city(base, cities):
    """Loose slug match used by both guide endpoints: exact, then
    spaces/dashes folded to underscores, then the longest startswith match
    in either direction ('Karachi, Pakistan' -> karachi, 'dera' ->
    dera_ismail_khan). Returns None when nothing fits.
    """
    norm = base.replace(" ", "_").replace("-", "_")
    if norm in cities:
        return norm
    best = None
    for key in cities:
        if base.startswith(key) or (len(base) >= 3 and key.startswith(base)):
            if best is None or len(key) > len(best):
                best = key
    return best


@bp.route("/growing-guides", methods=["GET"])
def growing_guides():
    """Index of every city that has a growing guide, grouped by province -
    powers the smart filters on /guides (province pills, live name search,
    sowing-this-month filter). Lightweight only; fetch
    /growing-guide?city=SLUG for one city's full notes.
    """
    cities, provinces = _load_city_guides()
    index = [
        {
            "slug": slug,
            "name": _pretty_city_name(slug),
            "province": guide["province"],
            "best_sowing_months": guide.get("best_sowing_months", []),
            "star_plants": guide.get("star_plants", []),
        }
        for slug, guide in sorted(cities.items())
    ]
    return jsonify({"provinces": provinces, "cities": index, "total": len(index)})


@bp.route("/growing-guide", methods=["GET"])
def growing_guide():
    """City-wise growing notes (Rabi/Kharif/transition guidance, local
    challenges and star plants) from data/city_growing_guides.json.
    Query: ?city=Karachi - matched loosely against the data slugs, so a
    resolved name like 'Karachi, Pakistan' works too. 404 when the city has
    no guide yet, so the frontend can simply hide the section.
    """
    city = (request.args.get("city") or "").strip().lower()
    if not city:
        return jsonify({"error": "Provide ?city=NAME"}), 400

    base = city.split(",")[0].strip()
    cities, _ = _load_city_guides()
    slug = _match_city(base, cities)
    if slug is None:
        return jsonify({"error": f"No growing guide for '{city}' yet."}), 404

    guide = cities[slug]
    return jsonify({
        "city": slug,
        "city_name": _pretty_city_name(slug),
        "province": guide["province"],
        "province_name": guide["province_name"],
        "guide": guide,
    })
