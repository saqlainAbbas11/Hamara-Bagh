"""
Weather / climate data via Open-Meteo (https://open-meteo.com) - free, no API
key, generous rate limits. This is the backbone of the location-aware
recommendation engine.

Two calls are made:
  1. Geocoding API - turn a city name into lat/lon
  2. Forecast API   - current conditions + 16-day daily forecast, used to
     approximate the near-term climate a plant would actually experience
"""
import statistics

import requests
from flask import current_app

from app.services.cache_service import cached_fetch

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Fixed 5-year window for the hardiness estimate - stable enough to cache
# for a month, recent enough to reflect the current climate.
HARDINESS_START = "2019-01-01"
HARDINESS_END = "2023-12-31"


def geocode_city(city_name: str):
    """Return {'lat', 'lon', 'name', 'country'} for a city name, or a dict
    with 'found': False / 'network_error': True - never raises, so a flaky
    connection degrades gracefully instead of crashing the request.
    """

    def _fetch():
        resp = requests.get(
            GEOCODE_URL,
            params={"name": city_name, "count": 1, "language": "en", "format": "json"},
            timeout=current_app.config["HTTP_TIMEOUT_SECONDS"],
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        if not results:
            return {"found": False}
        top = results[0]
        return {
            "found": True,
            "lat": top["latitude"],
            "lon": top["longitude"],
            "name": top.get("name"),
            "country": top.get("country"),
            "admin1": top.get("admin1"),
        }

    key = city_name.strip().lower()
    try:
        data, _ = cached_fetch("openmeteo_geocode", key, _fetch)
        return data
    except requests.RequestException as exc:
        return {"found": False, "network_error": True, "message": str(exc)}


def get_climate_snapshot(lat: float, lon: float):
    """Return a simplified climate snapshot for the location:
    current temp/humidity + 16-day forecast averages for max/min temp,
    precipitation and humidity. Used to classify the growing environment.
    """

    def _fetch():
        resp = requests.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean",
                "forecast_days": 16,
                "timezone": "auto",
            },
            timeout=current_app.config["HTTP_TIMEOUT_SECONDS"],
        )
        resp.raise_for_status()
        return resp.json()

    key = f"{round(lat, 2)}_{round(lon, 2)}"
    try:
        raw, _ = cached_fetch("openmeteo_forecast", key, _fetch)
    except requests.RequestException:
        return None

    if not raw or "daily" not in raw:
        return None

    daily = raw["daily"]
    max_temps = [t for t in daily.get("temperature_2m_max", []) if t is not None]
    min_temps = [t for t in daily.get("temperature_2m_min", []) if t is not None]
    precip = [p for p in daily.get("precipitation_sum", []) if p is not None]
    humidity = [h for h in daily.get("relative_humidity_2m_mean", []) if h is not None]

    if not max_temps or not min_temps:
        return None

    return {
        "current_temp_c": raw.get("current", {}).get("temperature_2m"),
        "current_humidity_pct": raw.get("current", {}).get("relative_humidity_2m"),
        "avg_max_temp_c": round(statistics.mean(max_temps), 1),
        "avg_min_temp_c": round(statistics.mean(min_temps), 1),
        "peak_max_temp_c": round(max(max_temps), 1),
        "lowest_min_temp_c": round(min(min_temps), 1),
        "total_precip_mm_16d": round(sum(precip), 1) if precip else 0,
        "avg_humidity_pct": round(statistics.mean(humidity), 1) if humidity else None,
    }


def get_air_quality(lat: float, lon: float):
    """Return a simplified air quality reading (PM2.5-based) for the
    location. Free, no API key. Useful because Lahore/urban smog genuinely
    affects which plants do well outdoors.
    """

    def _fetch():
        resp = requests.get(
            AIR_QUALITY_URL,
            params={"latitude": lat, "longitude": lon, "current": "pm2_5,pm10,us_aqi"},
            timeout=current_app.config["HTTP_TIMEOUT_SECONDS"],
        )
        resp.raise_for_status()
        return resp.json()

    key = f"{round(lat, 2)}_{round(lon, 2)}"
    try:
        raw, _ = cached_fetch("openmeteo_air_quality", key, _fetch)
    except requests.RequestException:
        return None

    current = (raw or {}).get("current", {})
    us_aqi = current.get("us_aqi")
    if us_aqi is None:
        return None

    if us_aqi <= 50:
        level = "good"
    elif us_aqi <= 100:
        level = "moderate"
    elif us_aqi <= 150:
        level = "unhealthy_for_sensitive_groups"
    else:
        level = "unhealthy"

    return {
        "us_aqi": us_aqi,
        "pm2_5": current.get("pm2_5"),
        "pm10": current.get("pm10"),
        "level": level,
    }


def get_hardiness_profile(lat: float, lon: float):
    """Approximate hardiness profile from 5 years of historical daily data
    (Open-Meteo archive - free, no key). Answers "how cold does it actually
    get here?" - the question a USDA zone answers elsewhere, but no public
    hardiness map exists for Pakistan (see README roadmap).
    """

    def _fetch():
        resp = requests.get(
            ARCHIVE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": HARDINESS_START,
                "end_date": HARDINESS_END,
                "daily": "temperature_2m_min,temperature_2m_max",
                "timezone": "auto",
            },
            timeout=current_app.config["HTTP_TIMEOUT_SECONDS"],
        )
        resp.raise_for_status()
        return resp.json()

    key = f"{round(lat, 2)}_{round(lon, 2)}"
    try:
        raw, _ = cached_fetch("openmeteo_archive", key, _fetch)
    except requests.RequestException:
        return None

    daily = (raw or {}).get("daily") or {}
    mins = [m for m in daily.get("temperature_2m_min") or [] if m is not None]
    maxs = [m for m in daily.get("temperature_2m_max") or [] if m is not None]
    if not mins:
        return None

    extreme_min = round(min(mins), 1)
    avg_high = round(statistics.mean(maxs), 1) if maxs else None

    # USDA zones: each zone spans 10F starting at -60F; a/b denotes halves.
    fahrenheit = extreme_min * 9 / 5 + 32
    zone_float = (fahrenheit + 60) / 10 + 1
    zone_num = max(1, min(13, int(zone_float)))
    half = "a" if zone_float - int(zone_float) < 0.5 else "b"
    usda_zone = f"{zone_num}{half}"

    if extreme_min >= 10:
        zone_label = "tropical lowland - frost essentially never occurs"
    elif extreme_min >= 4:
        zone_label = "subtropical - frost is rare"
    elif extreme_min >= 0:
        zone_label = "mild winters - light frost possible"
    elif extreme_min >= -6:
        zone_label = "cold winters - regular frost"
    else:
        zone_label = "severe winters - hard freezes and snow"

    return {
        "period": f"{HARDINESS_START} to {HARDINESS_END}",
        "extreme_min_c": extreme_min,
        "avg_daytime_high_c": avg_high,
        "usda_zone_equivalent": usda_zone,
        "zone_label": zone_label,
    }
