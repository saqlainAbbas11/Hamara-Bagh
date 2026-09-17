import json
from datetime import datetime, timezone, timedelta

from flask import current_app

from app.extensions import db
from app.models import ApiCache


def _now():
    return datetime.now(timezone.utc)


def get_cached(source: str, cache_key: str):
    """Return cached response dict if present and not expired, else None."""
    row = ApiCache.query.filter_by(source=source, cache_key=cache_key).first()
    if not row:
        return None

    ttl_by_source = current_app.config.get("CACHE_TTL_BY_SOURCE", {})
    ttl = ttl_by_source.get(source, current_app.config.get("API_CACHE_TTL_SECONDS", 86400))
    fetched_at = row.fetched_at
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)

    if _now() - fetched_at > timedelta(seconds=ttl):
        return None  # expired - caller should refetch and overwrite

    try:
        return json.loads(row.response_json)
    except (TypeError, ValueError):
        return None


def set_cached(source: str, cache_key: str, response_obj):
    """Insert or update a cache row for (source, cache_key)."""
    row = ApiCache.query.filter_by(source=source, cache_key=cache_key).first()
    payload = json.dumps(response_obj)

    if row:
        row.response_json = payload
        row.fetched_at = _now()
    else:
        row = ApiCache(source=source, cache_key=cache_key, response_json=payload, fetched_at=_now())
        db.session.add(row)

    db.session.commit()
    return response_obj


def cached_fetch(source: str, cache_key: str, fetch_fn):
    """Get from cache, or call fetch_fn() and store the result.

    fetch_fn should return a JSON-serializable object, or raise an exception
    on failure (caller should catch and handle gracefully - we never want a
    flaky third-party API to break the whole app).
    """
    cached = get_cached(source, cache_key)
    if cached is not None:
        return cached, True  # (data, was_cached)

    fresh = fetch_fn()
    set_cached(source, cache_key, fresh)
    return fresh, False
