"""
GBIF (gbif.org) and iNaturalist (inaturalist.org) - both free, no API key,
backed by institutions, so much more reliable uptime than Trefle/Perenual.
Best for scientific accuracy, distribution, and photos - not for beginner
care advice, which is what our local dataset + Perenual are for.
"""
import requests
from flask import current_app

from app.services.cache_service import cached_fetch

GBIF_SPECIES_MATCH_URL = "https://api.gbif.org/v1/species/match"
GBIF_OCCURRENCE_URL = "https://api.gbif.org/v1/occurrence/search"
INAT_TAXA_URL = "https://api.inaturalist.org/v1/taxa"


def gbif_species_match(scientific_or_common_name: str):
    """Resolve a plant name to GBIF's canonical taxonomy record."""

    def _fetch():
        resp = requests.get(
            GBIF_SPECIES_MATCH_URL,
            params={"name": scientific_or_common_name, "kingdom": "Plantae"},
            timeout=current_app.config["HTTP_TIMEOUT_SECONDS"],
        )
        resp.raise_for_status()
        return resp.json()

    key = scientific_or_common_name.strip().lower()
    try:
        data, was_cached = cached_fetch("gbif", key, _fetch)
        return {"cached": was_cached, "data": data}
    except requests.RequestException as exc:
        return {"error": True, "message": f"GBIF unavailable: {exc}", "data": None}


def gbif_occurrence_near(lat: float, lon: float, species_key: int = None, radius_km: float = 50):
    """Check whether a species (or plants generally) have been recorded
    growing naturally near a given location - a nice signal for 'is this
    plant actually suited to my region' beyond just temperature matching.
    """

    def _fetch():
        params = {
            "decimalLatitude": f"{lat - radius_km/111:.4f},{lat + radius_km/111:.4f}",
            "decimalLongitude": f"{lon - radius_km/111:.4f},{lon + radius_km/111:.4f}",
            "kingdomKey": 6,  # Plantae
            "limit": 20,
        }
        if species_key:
            params["taxonKey"] = species_key
        resp = requests.get(GBIF_OCCURRENCE_URL, params=params, timeout=current_app.config["HTTP_TIMEOUT_SECONDS"])
        resp.raise_for_status()
        return resp.json()

    key = f"{round(lat,2)}_{round(lon,2)}_{species_key or 'any'}"
    try:
        data, was_cached = cached_fetch("gbif_occurrence", key, _fetch)
        return {"cached": was_cached, "data": data}
    except requests.RequestException as exc:
        return {"error": True, "message": f"GBIF unavailable: {exc}", "data": None}


def inaturalist_taxa_search(query: str):
    """Search iNaturalist for a plant - good source of real-world photos
    and common names in multiple languages/regions.
    """

    def _fetch():
        resp = requests.get(
            INAT_TAXA_URL,
            params={"q": query, "iconic_taxa": "Plantae", "per_page": 5},
            timeout=current_app.config["HTTP_TIMEOUT_SECONDS"],
        )
        resp.raise_for_status()
        return resp.json()

    key = query.strip().lower()
    try:
        data, was_cached = cached_fetch("inaturalist", key, _fetch)
        return {"cached": was_cached, "data": data}
    except requests.RequestException as exc:
        return {"error": True, "message": f"iNaturalist unavailable: {exc}", "data": None}
