"""
Trefle API (trefle.io) - included for completeness, but as of 2025 its
search endpoint has intermittently returned server errors, and the project
has previously gone offline entirely for extended periods. Treat this as a
best-effort bonus source, never a dependency. Requires TREFLE_TOKEN.
"""
import requests
from flask import current_app

from app.services.cache_service import cached_fetch

BASE_URL = "https://trefle.io/api/v1"


def is_enabled():
    return bool(current_app.config.get("TREFLE_TOKEN"))


def search_plants(query: str):
    if not is_enabled():
        return {"enabled": False, "reason": "TREFLE_TOKEN not set", "data": []}

    def _fetch():
        resp = requests.get(
            f"{BASE_URL}/plants/search",
            params={"token": current_app.config["TREFLE_TOKEN"], "q": query},
            timeout=current_app.config["HTTP_TIMEOUT_SECONDS"],
        )
        resp.raise_for_status()
        return resp.json()

    key = query.strip().lower()
    try:
        data, was_cached = cached_fetch("trefle", key, _fetch)
        return {"enabled": True, "cached": was_cached, "data": data}
    except requests.RequestException as exc:
        # Trefle is known to be flaky - fail soft, never break the request
        return {"enabled": True, "error": True, "message": f"Trefle unavailable: {exc}", "data": []}
