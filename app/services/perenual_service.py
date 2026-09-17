"""
Perenual API (https://perenual.com/docs/api) - free tier ~100 req/day,
full care detail only for roughly the first 3000 species IDs. We cache
every response so a given search/species is only ever fetched once.
Requires PERENUAL_API_KEY - if unset, this service is disabled and callers
should fall back to local data gracefully.
"""
import requests
from flask import current_app

from app.services.cache_service import cached_fetch

BASE_URL = "https://perenual.com/api/v2"


def is_enabled():
    return bool(current_app.config.get("PERENUAL_API_KEY"))


def search_species(query: str, page: int = 1):
    if not is_enabled():
        return {"enabled": False, "reason": "PERENUAL_API_KEY not set", "data": []}

    def _fetch():
        resp = requests.get(
            f"{BASE_URL}/species-list",
            params={"key": current_app.config["PERENUAL_API_KEY"], "q": query, "page": page},
            timeout=current_app.config["HTTP_TIMEOUT_SECONDS"],
        )
        resp.raise_for_status()
        return resp.json()

    key = f"search_{query.strip().lower()}_{page}"
    try:
        data, was_cached = cached_fetch("perenual", key, _fetch)
        return {"enabled": True, "cached": was_cached, "data": data}
    except requests.RequestException as exc:
        return {"enabled": True, "error": True, "message": f"Perenual unavailable: {exc}", "data": []}


def get_species_detail(species_id: int):
    if not is_enabled():
        return {"enabled": False, "reason": "PERENUAL_API_KEY not set", "data": None}

    def _fetch():
        resp = requests.get(
            f"{BASE_URL}/species/details/{species_id}",
            params={"key": current_app.config["PERENUAL_API_KEY"]},
            timeout=current_app.config["HTTP_TIMEOUT_SECONDS"],
        )
        resp.raise_for_status()
        return resp.json()

    key = f"detail_{species_id}"
    try:
        data, was_cached = cached_fetch("perenual", key, _fetch)
        return {"enabled": True, "cached": was_cached, "data": data}
    except requests.RequestException as exc:
        return {"enabled": True, "error": True, "message": f"Perenual unavailable: {exc}", "data": None}
