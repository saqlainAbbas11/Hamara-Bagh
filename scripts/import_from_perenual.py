"""
Bulk-expand data/plants.json using the Perenual API.

Requires a free PERENUAL_API_KEY (https://perenual.com/docs/api) in your
environment or .env file. The free tier allows ~100 requests/day and each
page of results costs ONE request - so --pages 3 is 3 requests.

Usage:
    python scripts/import_from_perenual.py --pages 3 --dry-run   # preview counts only
    python scripts/import_from_perenual.py --pages 3            # merge into data/plants.json
    python scripts/import_from_perenual.py --pages 3 --out data/plants_import.json

After importing, load the new plants into the database:
    python scripts/seed_db.py

Notes:
  * Mapping is best-effort: Perenual doesn't provide Celsius ranges, so its
    USDA hardiness zones are converted to approximate minimum temperatures.
  * Species already present (matched by lowercased common name) are skipped.
  * Entries land in exactly the plants.json schema; unknown fields are null,
    which the recommendation engine treats as neutral rather than a penalty.
"""
import argparse
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

BASE_URL = "https://perenual.com/api/v2"
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "..", "data", "plants.json")

WATERING_MAP = {
    "frequent": "high",
    "average": "medium",
    "minimum": "low",
    "none": "very_low",
}

SUNLIGHT_MAP = {
    "full sun": "full_sun",
    "sun": "full_sun",
    "part shade": "part_shade",
    "partial shade": "part_shade",
    "sun-part shade": "part_shade",
    "filtered shade": "part_shade",
    "full shade": "full_shade",
}

CATEGORY_HINTS = [
    ("houseplant", "houseplant"),
    ("indoor", "houseplant"),
    ("succulent", "succulent"),
    ("cactus", "succulent"),
    ("vegetable", "vegetable"),
    ("herb", "herb"),
    ("flower", "flower"),
    ("tree", "tree"),
    ("shrub", "tree"),
]


def usda_zone_to_min_c(zone):
    """Approximate the coldest temperature a USDA zone sees, in Celsius
    (lower bound of the zone). Zone 10a -> about -1 C."""
    try:
        z = float(str(zone).strip().rstrip("ab").strip())
    except (TypeError, ValueError):
        return None
    lower_bound_f = -60 + 10 * (z - 1)
    return round((lower_bound_f - 32) * 5 / 9, 1)


def guess_category(species):
    for field in ("type", "plant_type", "category"):
        value = str(species.get(field) or "").lower()
        for hint, category in CATEGORY_HINTS:
            if hint in value:
                return category
    return "other"


def map_species(species):
    """Map one Perenual species record onto the plants.json schema."""
    scientific = species.get("scientific_name")
    if isinstance(scientific, list):
        scientific = scientific[0] if scientific else None

    sunlight_raw = species.get("sunlight") or []
    sunlight = None
    if sunlight_raw:
        sunlight = SUNLIGHT_MAP.get(str(sunlight_raw[0]).strip().lower())

    cycle = str(species.get("cycle") or "").lower()
    season = "perennial" if "perennial" in cycle else None

    hardiness = species.get("hardiness") or {}

    return {
        "common_name": (species.get("common_name") or "").strip(),
        "scientific_name": scientific,
        "category": guess_category(species),
        "sunlight": sunlight,
        "water_need": WATERING_MAP.get(str(species.get("watering") or "").strip().lower(), "medium"),
        "min_temp_c": usda_zone_to_min_c(hardiness.get("min")),
        "max_temp_c": None,
        "ideal_temp_min_c": None,
        "ideal_temp_max_c": None,
        "humidity_pref": "medium",
        "soil_type": None,
        "difficulty": "medium",
        "season": season,
        "sow_months": [],
        "days_to_maturity": None,
        "toxic_to_pets": False,
        "pollution_tolerant": False,
        "container_friendly": True,
        "description": (species.get("description") or "").strip() or None,
        "care_tips": None,
        "image_url": (species.get("default_image") or {}).get("original_url"),
    }


def fetch_page(api_key, page):
    resp = requests.get(
        f"{BASE_URL}/species-list",
        params={"key": api_key, "page": page},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Import plants from Perenual into data/plants.json")
    parser.add_argument("--pages", type=int, default=3, help="how many result pages to fetch (1 request each)")
    parser.add_argument("--out", default=DEFAULT_OUT, help="output JSON file (default: data/plants.json)")
    parser.add_argument("--dry-run", action="store_true", help="fetch + map but don't write anything")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between API requests (be polite)")
    args = parser.parse_args()

    api_key = os.environ.get("PERENUAL_API_KEY")
    if not api_key:
        print("PERENUAL_API_KEY is not set.")
        print("Get a free key at https://perenual.com/docs/api and put it in .env as:")
        print("    PERENUAL_API_KEY=your-key-here")
        sys.exit(1)

    out_path = os.path.abspath(args.out)
    with open(out_path, "r", encoding="utf-8") as f:
        existing = json.load(f)

    existing_names = {p.get("common_name", "").strip().lower() for p in existing}
    new_entries = []
    skipped = 0
    fetch_failure = None

    for page in range(1, args.pages + 1):
        try:
            payload = fetch_page(api_key, page)
        except requests.RequestException as exc:
            fetch_failure = f"page {page}: {exc}"
            break

        items = payload.get("data") or []
        if not items:
            break

        for species in items:
            mapped = map_species(species)
            name = mapped["common_name"]
            if not name or not mapped["scientific_name"]:
                skipped += 1
                continue
            if name.lower() in existing_names:
                skipped += 1
                continue
            existing_names.add(name.lower())
            new_entries.append(mapped)

        print(f"page {page}: {len(items)} species fetched, {len(new_entries)} new so far")
        time.sleep(args.delay)

    print("-" * 60)
    print(f"New species mapped: {len(new_entries)}")
    print(f"Skipped (duplicates / incomplete): {skipped}")
    if fetch_failure:
        print(f"Stopped early - {fetch_failure}")

    if args.dry_run:
        print("Dry run - nothing written.")
        return

    merged = existing + new_entries
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(merged)} plants to {out_path}")
    print("Now run: python scripts/seed_db.py")


if __name__ == "__main__":
    main()
