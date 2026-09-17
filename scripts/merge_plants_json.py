"""
Validate and merge new plant entries (e.g. from an LLM research batch) into
data/plants.json.

Every entry is checked against the dataset schema: required keys, allowed
enum values, temperature ordering, sow-month ranges and duplicate names.
Survivors are appended; anything invalid is reported and skipped - never
written. The 'sources' field (optional, ignored by the app) is kept for
provenance and cleaned from markdown-link form to plain URLs.

Usage:
    python scripts/merge_plants_json.py new_batch.json [more.json ...]
    python scripts/merge_plants_json.py new_batch.json --dry-run

After merging, run scripts/seed_db.py to load the dataset into the database.
"""
import argparse
import json
import os
import re
import sys
from urllib.parse import unquote

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "plants.json")

REQUIRED_KEYS = [
    "common_name", "scientific_name", "category", "sunlight", "water_need",
    "min_temp_c", "max_temp_c", "ideal_temp_min_c", "ideal_temp_max_c",
    "humidity_pref", "soil_type", "difficulty", "season", "sow_months",
    "days_to_maturity", "toxic_to_pets", "pollution_tolerant",
    "container_friendly", "description", "care_tips",
]

ENUMS = {
    "category": {"vegetable", "herb", "flower", "tree", "succulent", "houseplant"},
    "sunlight": {"full_sun", "part_shade", "full_shade"},
    "water_need": {"very_low", "low", "medium", "high"},
    "humidity_pref": {"very_low", "low", "medium", "high"},
    "difficulty": {"very_easy", "easy", "medium", "hard"},
    "season": {"rabi", "kharif", "rabi_and_kharif", "perennial"},
}

BOOL_KEYS = ["toxic_to_pets", "pollution_tolerant", "container_friendly"]

MARKDOWN_LINK = re.compile(r"^\[[^\]]*\]\((.*?)\)$")
GOOGLE_SEARCH_LINK = re.compile(r"^https?://(?:www\.)?google\.[a-z.]+/search\?.*\bq=(https?://\S+)$", re.IGNORECASE)


def _unwrap_google(url):
    """LLM output sometimes wraps sources as google.com/search?q=<url> -
    unwrap those redirects so the stored source is the real page."""
    match = GOOGLE_SEARCH_LINK.match(url)
    return unquote(match.group(1)) if match else url


def normalize_sources(sources):
    """Turn markdown-style links into plain URLs, keep everything else as-is."""
    if not isinstance(sources, list):
        return None
    cleaned = []
    for item in sources:
        if not isinstance(item, str):
            continue
        match = MARKDOWN_LINK.match(item.strip())
        url = match.group(1) if match else item.strip()
        cleaned.append(_unwrap_google(url))
    return cleaned


def validate(entry, seen_names):
    """Return (entry, None) if the entry is valid, else (None, error_message)."""
    if not isinstance(entry, dict):
        return None, "entry is not a JSON object"

    name = entry.get("common_name")
    for key in REQUIRED_KEYS:
        if key not in entry:
            return None, f"missing key '{key}'"
    if not isinstance(name, str) or not name.strip():
        return None, "common_name must be a non-empty string"

    name_key = name.strip().lower()
    if name_key in seen_names:
        return None, f"duplicate name '{name}' (already in the dataset or this batch)"

    for field, allowed in ENUMS.items():
        if entry.get(field) not in allowed:
            return None, f"invalid {field} '{entry.get(field)}' (allowed: {sorted(allowed)})"

    temps = {}
    for field in ("min_temp_c", "max_temp_c", "ideal_temp_min_c", "ideal_temp_max_c"):
        value = entry.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None, f"{field} must be a number"
        temps[field] = value
    if not (temps["min_temp_c"] < temps["ideal_temp_min_c"] <= temps["ideal_temp_max_c"] < temps["max_temp_c"]):
        return None, ("temperature ordering violated - need "
                      "min < ideal_min <= ideal_max < max")

    months = entry.get("sow_months")
    if not isinstance(months, list) or not all(isinstance(m, int) and 1 <= m <= 12 for m in months):
        return None, "sow_months must be a list of integers 1-12"

    maturity = entry.get("days_to_maturity")
    if maturity is not None and (not isinstance(maturity, int) or isinstance(maturity, bool)):
        return None, "days_to_maturity must be an integer or null"

    for field in BOOL_KEYS:
        if not isinstance(entry.get(field), bool):
            return None, f"{field} must be true or false"

    if not isinstance(entry.get("description"), str) or not entry["description"].strip():
        return None, "description must be a non-empty string"
    if not isinstance(entry.get("care_tips"), str) or not entry["care_tips"].strip():
        return None, "care_tips must be a non-empty string"

    entry["common_name"] = name.strip()
    sources = normalize_sources(entry.get("sources"))
    if sources:
        entry["sources"] = sources
    else:
        entry.pop("sources", None)

    return entry, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", help="JSON file(s) containing an array of plants")
    parser.add_argument("--dry-run", action="store_true", help="validate only, write nothing")
    args = parser.parse_args()

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    seen_names = {entry["common_name"].strip().lower() for entry in dataset}
    added, skipped = [], []

    for path in args.files:
        with open(path, "r", encoding="utf-8") as f:
            incoming = json.load(f)
        if not isinstance(incoming, list):
            print(f"!! {path}: top level must be a JSON array, skipping whole file")
            continue

        for entry in incoming:
            valid, error = validate(entry, seen_names)
            if valid is None:
                skipped.append((path, error))
                continue
            seen_names.add(valid["common_name"].lower())
            added.append(valid)

    print(f"Validated: {len(added)} to add, {len(skipped)} skipped")
    for path, error in skipped:
        print(f"  - skipped ({os.path.basename(path)}): {error}")

    if args.dry_run:
        print("Dry run - nothing written.")
        return

    if not added:
        print("Nothing to merge.")
        return

    dataset.extend(added)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Merged. data/plants.json now has {len(dataset)} plants.")
    print("Next step: python scripts/seed_db.py")


if __name__ == "__main__":
    sys.exit(main())
