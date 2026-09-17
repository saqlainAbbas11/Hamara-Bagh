"""Minimal translation layer: data/strings.json + t().

Deliberately not gettext - adding a language should be as simple as adding
a column to one JSON file so non-programmers can contribute translations
(the README calls out Urdu support as a differentiator for this project).
"""
import json
import os

from flask import request

STRINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "strings.json")
SUPPORTED_LANGUAGES = ("en", "ur")

_strings_cache = None


def _load_strings():
    global _strings_cache
    if _strings_cache is None:
        with open(STRINGS_PATH, "r", encoding="utf-8") as f:
            _strings_cache = json.load(f)
    return _strings_cache


def available_languages():
    return list(SUPPORTED_LANGUAGES)


def t(key: str, lang: str = "en", **fmt) -> str:
    """Translate a key to the requested language, falling back to English,
    then to the bare key if it doesn't exist at all."""
    entry = _load_strings().get(key)
    if not isinstance(entry, dict):
        return key
    text = entry.get(lang) or entry.get("en") or key
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, IndexError):
            return text
    return text


def resolve_lang() -> str:
    """?lang=ur from the query string, defaulting to English for anything
    unsupported."""
    lang = (request.args.get("lang") or "en").strip().lower()
    return lang if lang in SUPPORTED_LANGUAGES else "en"
