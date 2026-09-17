import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load .env from the project root before anything reads os.environ.
# `python run.py` does NOT load .env automatically the way `flask run` does,
# so without this call any keys placed in .env are silently ignored.
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'greenmitra.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # External API keys - all optional. App works with pure local data if unset.
    PERENUAL_API_KEY = os.environ.get("PERENUAL_API_KEY", "")
    TREFLE_TOKEN = os.environ.get("TREFLE_TOKEN", "")

    # Optional free Hugging Face token - powers the AI "plant doctor" answers
    # on /troubleshoot. Create a fine-grained token with the "Make calls to
    # Inference Providers" permission at https://hf.co/settings/tokens
    HUGGINGFACE_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", "")
    # First model tried; ai_service falls back to other widely-served models
    # when the router reports this one is not supported by any provider.
    HF_MODEL = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")

    # LLM answers take longer than the 8s we allow weather/taxonomy calls.
    AI_TIMEOUT_SECONDS = int(os.environ.get("AI_TIMEOUT_SECONDS", 60))

    # Optional admin token gating the plant-submission review endpoints.
    # If unset (typical local dev), those endpoints stay open.
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

    # Default TTL (seconds) for cached external API responses before refetching
    API_CACHE_TTL_SECONDS = int(os.environ.get("API_CACHE_TTL_SECONDS", 60 * 60 * 24))  # 24h default

    # Per-source TTL overrides: volatile data stays fresh while stable
    # reference data is cached far longer, keeping us well under every
    # free-tier rate limit without serving stale weather.
    CACHE_TTL_BY_SOURCE = {
        "openmeteo_geocode": 60 * 60 * 24 * 30,   # city coordinates never change
        "openmeteo_forecast": 60 * 60,            # 1h - keeps "current conditions" fresh
        "openmeteo_air_quality": 60 * 60,         # 1h
        "openmeteo_archive": 60 * 60 * 24 * 30,   # historical climate barely changes
        "wikipedia": 60 * 60 * 24 * 30,
        "gbif": 60 * 60 * 24 * 30,
        "gbif_occurrence": 60 * 60 * 24 * 7,
        "inaturalist": 60 * 60 * 24 * 7,
        "perenual": 60 * 60 * 24 * 7,             # protect the ~100 req/day free tier
        "trefle": 60 * 60 * 24 * 7,
    }

    # Timeout for any outbound HTTP call to a third-party API
    HTTP_TIMEOUT_SECONDS = 8

    # Journal photo uploads (stored under instance/uploads, served at /uploads/...)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "uploads")
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024  # 6 MB per request
