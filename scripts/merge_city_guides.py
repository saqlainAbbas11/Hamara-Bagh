"""Merge a province-organised city-guide batch into data/city_growing_guides.json.

Usage:
    python scripts/merge_city_guides.py new_batch.json [--dry-run]

Incoming batch shape (province -> city -> guide):

    {
      "sindh": {
        "sukkur": {
          "growing_notes": {"rabi": "...", "kharif": "...", "transition": "..."},
          "best_sowing_months": [2, 3, 4, 9, 10, 11],
          "challenges": ["..."],
          "star_plants": ["Okra (Bhindi)", "..."]
        }
      }
    }

The stored file is province-nested:
    {"provinces": {"sindh": {"name": ..., "name_ur": ..., "cities": {...}}}}

Existing cities are skipped (first version wins — curated entries are never
overwritten). The legacy flat file (city -> guide) is upgraded in place the
first time this script runs. Entries are validated and cleaned (trimmed
strings, sorted unique months) before writing.
"""
import argparse
import json
import os
import sys

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "city_growing_guides.json")

PROVINCE_ORDER = [
    "punjab",
    "sindh",
    "khyber_pakhtunkhwa",
    "balochistan",
    "gilgit_baltistan",
    "islamabad_capital_territory",
]

PROVINCE_META = {
    "punjab": {"name": "Punjab", "name_ur": "پنجاب"},
    "sindh": {"name": "Sindh", "name_ur": "سندھ"},
    "khyber_pakhtunkhwa": {"name": "Khyber Pakhtunkhwa", "name_ur": "خیبر پختونخوا"},
    "balochistan": {"name": "Balochistan", "name_ur": "بلوچستان"},
    "gilgit_baltistan": {"name": "Gilgit-Baltistan", "name_ur": "گلگت بلتستان"},
    "islamabad_capital_territory": {"name": "Islamabad Capital Territory", "name_ur": "اسلام آباد"},
}

# Where the original flat-file cities belong (one-time upgrade path).
LEGACY_PROVINCE = {
    "lahore": "punjab",
    "multan": "punjab",
    "faisalabad": "punjab",
    "murree": "punjab",
    "karachi": "sindh",
    "hyderabad": "sindh",
    "peshawar": "khyber_pakhtunkhwa",
    "quetta": "balochistan",
    "gilgit": "gilgit_baltistan",
    "islamabad": "islamabad_capital_territory",
}

SEASON_KEYS = ("rabi", "kharif", "transition")

# Map star-plant spellings onto the exact common_name used in data/plants.json,
# so guide chips can link to plant cards. Unknown names are kept verbatim.
STAR_ALIASES = {
    "holy basil (tulsi)": "Tulsi (Holy Basil)",
}


def _star_name(name):
    cleaned = _clean(name)
    return STAR_ALIASES.get(cleaned.lower(), cleaned)


def _clean(value):
    return value.strip() if isinstance(value, str) else value


def validate_city(slug, guide):
    """Return (cleaned_guide, None) or (None, reason)."""
    if not isinstance(guide, dict):
        return None, "guide is not an object"
    notes = guide.get("growing_notes")
    if not isinstance(notes, dict) or not any(_clean(notes.get(k)) for k in ("rabi", "kharif")):
        return None, "missing growing_notes (needs at least rabi + kharif)"
    months = guide.get("best_sowing_months")
    if not isinstance(months, list) or not months:
        return None, "missing best_sowing_months"
    try:
        months = sorted({int(m) for m in months})
    except (TypeError, ValueError):
        return None, "best_sowing_months must be integers"
    if any(m < 1 or m > 12 for m in months):
        return None, "best_sowing_months out of range"
    challenges = guide.get("challenges")
    if not isinstance(challenges, list) or not all(isinstance(c, str) and c.strip() for c in challenges):
        return None, "missing challenges"
    stars = guide.get("star_plants")
    if not isinstance(stars, list) or not all(isinstance(s, str) and s.strip() for s in stars):
        return None, "missing star_plants"
    cleaned = {
        "growing_notes": {k: _clean(notes.get(k, "")) for k in SEASON_KEYS},
        "best_sowing_months": months,
        "challenges": [_clean(c) for c in challenges],
        "star_plants": [_star_name(s) for s in stars],
    }
    return cleaned, None


def load_existing():
    """Return {province: {city: guide}} from any stored format."""
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    provinces = {}
    if "provinces" in data:  # current nested format
        for prov, body in data["provinces"].items():
            provinces[prov] = dict(body.get("cities", {}))
    else:  # legacy flat format -> assign known provinces
        for city, guide in data.items():
            prov = LEGACY_PROVINCE.get(city)
            if prov is None:
                print(f"  ! legacy city '{city}' has no province mapping - skipped")
                continue
            provinces.setdefault(prov, {})[city] = guide
    return provinces


def main():
    parser = argparse.ArgumentParser(description="Merge province-organised city guides.")
    parser.add_argument("batch", help="JSON file with {province: {city: guide}}")
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    args = parser.parse_args()

    existing_before = load_existing()
    existing_cities = {c for cities in existing_before.values() for c in cities}

    with open(args.batch, "r", encoding="utf-8") as f:
        incoming = json.load(f)
    if not isinstance(incoming, dict):
        sys.exit("Batch must be a {province: {city: guide}} object.")

    added, skipped, invalid = {}, [], []
    for prov, cities in incoming.items():
        if not isinstance(cities, dict):
            invalid.append((prov, "(province level)", "province body is not an object"))
            continue
        for city, guide in cities.items():
            if city in existing_cities:
                skipped.append((prov, city))
                continue
            cleaned, reason = validate_city(city, guide)
            if reason:
                invalid.append((prov, city, reason))
                continue
            added.setdefault(prov, {})[city] = cleaned
            existing_cities.add(city)

    total_existing = sum(len(c) for c in existing_before.values())
    total_incoming = sum(len(c) for c in incoming.values() if isinstance(c, dict))
    print(f"existing: {total_existing} cities | incoming: {total_incoming}")
    print(f"\nADDED ({sum(len(c) for c in added.values())}):")
    for prov in sorted(added):
        print(f"  {prov}: {len(added[prov])} -> {', '.join(sorted(added[prov]))}")
    print(f"\nSKIPPED as duplicates ({len(skipped)}):")
    for prov, city in skipped:
        print(f"  {prov}/{city}")
    if invalid:
        print(f"\nINVALID ({len(invalid)}):")
        for prov, city, reason in invalid:
            print(f"  {prov}/{city}: {reason}")

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return

    merged = {p: dict(c) for p, c in existing_before.items()}
    for prov, cities in added.items():
        merged.setdefault(prov, {}).update(cities)

    ordered = PROVINCE_ORDER + [p for p in sorted(merged) if p not in PROVINCE_ORDER]
    out = {"provinces": {}}
    for prov in ordered:
        if prov not in merged:
            continue
        meta = PROVINCE_META.get(prov, {"name": prov.replace("_", " ").title(), "name_ur": ""})
        out["provinces"][prov] = {
            "name": meta["name"],
            "name_ur": meta["name_ur"],
            "cities": {city: merged[prov][city] for city in sorted(merged[prov])},
        }

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    grand_total = sum(len(c["cities"]) for c in out["provinces"].values())
    print(f"\nwrote {DATA_PATH}")
    print(f"provinces: {len(out['provinces'])} | cities total: {grand_total}")


if __name__ == "__main__":
    main()
