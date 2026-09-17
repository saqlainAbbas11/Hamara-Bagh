"""
Wikipedia REST API - free, no key, very reliable uptime. Great supplemental
source for a readable plant summary + lead image when our local dataset
description is thin.
"""
import requests
from flask import current_app

from app.services.cache_service import cached_fetch

SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"


def get_summary(title: str):
    def _fetch():
        resp = requests.get(
            SUMMARY_URL.format(title=title.replace(" ", "_")),
            timeout=current_app.config["HTTP_TIMEOUT_SECONDS"],
            headers={"User-Agent": "HamaraBagh-OpenSource-Project/1.0"},
        )
        if resp.status_code == 404:
            return {"found": False}
        resp.raise_for_status()
        data = resp.json()
        return {
            "found": True,
            "title": data.get("title"),
            "extract": data.get("extract"),
            "thumbnail": (data.get("thumbnail") or {}).get("source"),
            "page_url": (data.get("content_urls", {}).get("desktop") or {}).get("page"),
        }

    key = title.strip().lower()
    try:
        data, was_cached = cached_fetch("wikipedia", key, _fetch)
        return {"cached": was_cached, **data}
    except requests.RequestException as exc:
        return {"found": False, "error": True, "message": f"Wikipedia unavailable: {exc}"}
