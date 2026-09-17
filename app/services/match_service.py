"""The matchmaker engine behind /match.

Answers ("what are your conditions?") in, ranked plant matches out - combining
two datasets on one trait scale:

- data/flowers.json entries (via flower_service) - the ornamental catalog
- the curated DB plants (Plant model) - vegetables, herbs, fruit trees ...

The DB rows are normalized onto the same trait vocabulary (water rank, sun
hours, heat/frost rank, space flags) so one scoring engine covers both.
Scores are normalized to 100; hard mismatches (wrong space, toxic with pets,
thirsty plant with a nearly-never watering routine) are not shown as matches
but explained in an "avoid" list instead - negative recommendations, honestly.
"""
import json
import os

from app.models import Plant
from app.services import flower_service

_CITY_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "city_climate_reference.json")
_city_cache = None

WATER_RANK = {"very_low": 0, "low": 1, "medium": 2, "high": 3}
HEAT_RANK = {"low": 0, "medium": 1, "high": 2, "very_high": 3}
FROST_RANK = {"low": 0, "medium": 1, "high": 2}
DIFF_RANK = {"very_easy": 0, "easy": 1, "medium": 2, "hard": 3}

# questionnaire vocabulary
VALID_SPACE = ("balcony", "rooftop", "ground", "indoor")
VALID_SUN = ("full", "half", "shade", "unsure")
VALID_WATER = ("often", "sometimes", "rarely", "almost_never")
VALID_EXPERIENCE = ("first_time", "some", "confident")
VALID_PURPOSES = ("flowers", "vegetables", "herbs", "fruit", "indoor",
                  "trees", "cactus_succulents", "pollinator", "greenery")
VALID_PRIORITIES = ("save_water", "lots_of_flowers", "handle_heat",
                    "handle_cold", "low_maintenance", "fragrance")

SUN_HOURS = {"full": 8.0, "half": 4.5, "shade": 2.0, "unsure": 5.0}
WATER_SUPPLY = {"often": 3, "sometimes": 2, "rarely": 1, "almost_never": 0}
DIFF_SCORE = {
    "first_time": {0: 15, 1: 12, 2: 6, 3: 2},
    "some": {0: 13, 1: 15, 2: 12, 3: 6},
    "confident": {0: 12, 1: 14, 2: 15, 3: 13},
}

CATEGORY_EMOJI = {
    "vegetable": "🥬", "herb": "🌿", "flower": "🌸", "tree": "🌳",
    "succulent": "🌵", "houseplant": "🪴", "other": "🌱",
}
FRUIT_HINTS = ("lemon", "guava", "papaya", "coconut", "banana", "mango", "orange",
               "citrus", "peach", "plum", "apple", "apricot", "almond", "grape",
               "mulberry", "pomegranate", "fig", "date", "ber", "chikoo", "amrood")


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
def _cities() -> dict:
    global _city_cache
    if _city_cache is None:
        with open(_CITY_PATH, "r", encoding="utf-8") as fh:
            _city_cache = json.load(fh)
    return _city_cache


def city_info(city):
    """Exact (case-insensitive) -> prefix match against the reference cities."""
    key = (city or "").strip().lower()
    if not key:
        return None
    cities = _cities()
    if key in cities:
        return dict(cities[key], key=key)
    for ck, cv in cities.items():
        if key.startswith(ck) or ck in key:
            return dict(cv, key=ck)
    return None


# ---------------------------------------------------------------------------
# Candidate normalization (one trait shape for both datasets)
# ---------------------------------------------------------------------------
def _flower_candidate(f: dict) -> dict:
    return {
        "type": "flower", "id": f["slug"], "name": f["name"],
        "scientific": f["scientific"], "local_name": f.get("local_name"),
        "group": f["group"], "category": None,
        "water": f["water"], "water_rank": WATER_RANK[f["water"]],
        "sun": f["sun"], "sun_min": float(f["sun_hours_min"]),
        "difficulty": f["difficulty"], "diff_rank": DIFF_RANK[f["difficulty"]],
        "bloom_months": f["bloom_months"], "sow_months": f["sow_months"],
        "fragrant": f["fragrant"], "pollinator": f["pollinator"],
        "pet_safe": f["pet_safe"], "native": f["native"], "salt": f["salt_tolerant"],
        "pot": f["container"], "indoor": f["indoor"],
        "balcony": f["balcony"], "rooftop": f["rooftop"], "ground": f["ground"],
        "heat_rank": HEAT_RANK[f["heat_tolerance"]], "frost_rank": FROST_RANK[f["frost_tolerance"]],
        "plant_id": None,
    }


def _db_candidate(p: Plant, data: dict) -> dict:
    sun_map = {"full_sun": ("full", 6.0), "part_shade": ("part", 3.0), "full_shade": ("shade", 1.0)}
    sun, sun_min = sun_map.get(data.get("sunlight"), ("full", 4.0))

    max_t = data.get("max_temp_c")
    heat = 3 if (max_t or 0) >= 42 else 2 if (max_t or 0) >= 37 else 1 if (max_t or 0) >= 32 else 0
    min_t = data.get("min_temp_c")
    frost = 2 if (min_t is not None and min_t <= 0) else 1 if (min_t is not None and min_t <= 6) else 0

    category = data.get("category") or "other"
    name = (data.get("common_name") or "").lower()
    is_tree = category == "tree"
    indoor = category == "houseplant"
    water = data.get("water_need") or "medium"

    return {
        "type": "plant", "id": data["id"], "name": data["common_name"],
        "scientific": data.get("scientific_name"), "local_name": None,
        "group": None, "category": category,
        "water": water, "water_rank": WATER_RANK.get(water, 2),
        "sun": sun, "sun_min": sun_min,
        "difficulty": data.get("difficulty") or "easy",
        "diff_rank": DIFF_RANK.get(data.get("difficulty") or "easy", 1),
        "bloom_months": [], "sow_months": data.get("sow_months") or [],
        "fragrant": False, "pollinator": category in ("flower", "herb", "tree"),
        "pet_safe": not data.get("toxic_to_pets"),
        "native": any(h in name for h in ("neem", "tulsi")),
        "salt": False,
        "pot": bool(data.get("container_friendly")), "indoor": indoor,
        "balcony": (not indoor) and (not is_tree),
        "rooftop": (not indoor) and (not is_tree),
        "ground": not indoor,
        "heat_rank": heat, "frost_rank": frost,
        "plant_id": data["id"],
    }


def _candidate_pool():
    """All flowers + DB plants with one trait shape. When a DB plant shares a
    name with a catalog flower, the flower entry wins (it has bloom months)
    and inherits the DB id so the journal link still works."""
    pool = []
    by_name = {}
    for f in flower_service.all_flowers():
        c = _flower_candidate(f)
        by_name[c["name"].lower()] = c
        pool.append(c)
    for p in Plant.query.all():
        key = (p.common_name or "").lower()
        if key in by_name:
            if by_name[key]["plant_id"] is None:
                by_name[key]["plant_id"] = p.id
            continue
        pool.append(_db_candidate(p, p.to_dict()))
    return pool


# ---------------------------------------------------------------------------
# Purpose / priority tests
# ---------------------------------------------------------------------------
def _matches_purpose(c: dict, purpose: str) -> bool:
    g, cat = c.get("group"), c.get("category")
    name = c["name"].lower()
    if purpose == "flowers":
        return bool(c["bloom_months"]) or cat == "flower"
    if purpose == "vegetables":
        return cat == "vegetable"
    if purpose == "herbs":
        return cat == "herb"
    if purpose == "fruit":
        return g == "fruit" or (cat == "tree" and any(h in name for h in FRUIT_HINTS))
    if purpose == "indoor":
        return c["indoor"]
    if purpose == "trees":
        return g == "tree" or cat == "tree"
    if purpose == "cactus_succulents":
        return g in ("cactus", "succulent") or cat == "succulent"
    if purpose == "pollinator":
        return c["pollinator"]
    if purpose == "greenery":
        return c["indoor"] or g in ("palm", "indoor") or cat == "houseplant"
    return True


def _priority_test(c: dict, priority: str) -> (bool, str):
    if priority == "save_water":
        return c["water_rank"] <= 1, "Sips water — light on the bijli bill"
    if priority == "lots_of_flowers":
        return len(c["bloom_months"]) >= 4 or c.get("category") == "flower", "Gives you flowers for months"
    if priority == "handle_heat":
        return c["heat_rank"] >= 2, "Handles 40°C+ summers"
    if priority == "handle_cold":
        return c["frost_rank"] >= 1, "Shrugs off winter cold"
    if priority == "low_maintenance":
        return c["diff_rank"] <= 1 and c["water_rank"] <= 2, "Barely any fuss once planted"
    if priority == "fragrance":
        return c["fragrant"], "Fills the air with fragrance"
    return False, ""


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def _space_block(c: dict, space: str):
    """Hard space filter - returns an 'avoid' reason or None."""
    if space == "balcony" and not c["balcony"]:
        return "Wants more room than a balcony shelf"
    if space == "rooftop" and not c["rooftop"]:
        return "Too bulky or delicate for a rooftop"
    if space == "ground" and not c["ground"]:
        return "Grows best indoors — skip the garden bed"
    if space == "indoor" and not c["indoor"]:
        return "Not an indoor plant — needs open sun and air"
    return None


def _score(c: dict, ans: dict, city):
    """Returns (score, payload). score=None means the plant was excluded and
    payload['exclude'] explains why (for the honest 'avoid' list)."""
    reasons, warnings = [], []

    # --- water (25) ------------------------------------------------------
    uw, pw = WATER_SUPPLY[ans["water"]], c["water_rank"]
    if pw - uw >= 2:
        return None, {"exclude": "Drinks far more than your watering schedule allows"}
    if pw > uw:
        water_s = 8
        warnings.append("Will need a bit more watering than you planned")
    else:
        water_s = max(25 - (uw - pw) * 5, 6)
        if pw <= 1:
            reasons.append("Thrives on little water")
            if uw - pw >= 3:
                warnings.append("Hates wet feet — let the soil dry fully between waterings")

    # --- sun (20) ---------------------------------------------------------
    have, need = SUN_HOURS[ans["sun"]], c["sun_min"]
    if need > have:
        deficit = need - have
        if deficit >= 3:
            return None, {"exclude": "Needs far more direct sun than your spot gets"}
        sun_s = max(20 - deficit * 6, 4)
        warnings.append("Would prefer a sunnier spot than yours")
    else:
        spare = have - need
        penalty = 12 if (c["sun"] == "shade" and spare >= 3) else 5 if (c["sun"] == "part" and spare >= 4) else 0
        if penalty and spare >= 4:
            return None, {"exclude": "Wilts in full sun — needs a shaded corner"}
        sun_s = max(20 - spare * 1.2 - penalty, 6)
        if ans["sun"] == "full" and c["sun"] == "full":
            reasons.append("Loves the full-sun spot you have")

    # --- space (15) --------------------------------------------------------
    space_s = 15
    if ans["space"] == "indoor":
        reasons.append("Happy indoors")
    elif ans["space"] == "balcony" and c["pot"]:
        reasons.append("Happy in a balcony pot")
    elif ans["space"] == "rooftop" and (c["heat_rank"] >= 1 or c["water_rank"] <= 1):
        reasons.append("Built for a sunny rooftop")

    # --- experience (15) ---------------------------------------------------
    exp_s = DIFF_SCORE[ans["experience"]][c["diff_rank"]]
    if ans["experience"] == "first_time" and c["diff_rank"] <= 1:
        reasons.append("Very forgiving — great for a first garden")
    elif ans["experience"] == "first_time" and c["diff_rank"] >= 2:
        warnings.append("Needs some experience — expect a few mistakes")

    # --- purposes (10) -----------------------------------------------------
    if ans["purposes"]:
        matched = sum(1 for p in ans["purposes"] if _matches_purpose(c, p))
        purpose_s = 10.0 * matched / len(ans["purposes"])
    else:
        purpose_s = 10.0

    # --- priorities (15) ----------------------------------------------------
    prio_s, prio_reasons = 0.0, []
    if ans["priorities"]:
        for p in ans["priorities"]:
            ok, note = _priority_test(c, p)
            if ok:
                prio_s += 15.0 / len(ans["priorities"])
                prio_reasons.append(note)
    else:
        prio_s = 15.0
    reasons.extend(prio_reasons[:2])

    # --- city climate (10) --------------------------------------------------
    city_s = 0.0
    if city:
        smax = city.get("avg_summer_max_c", 30)
        wmin = city.get("avg_winter_min_c", 10)
        if smax >= 40:
            city_s += 5 if c["heat_rank"] >= 2 else 2 if c["heat_rank"] >= 1 else 0
        elif smax >= 37:
            city_s += 3 if c["heat_rank"] >= 2 else 0
        if wmin <= 2:
            city_s += 5 if c["frost_rank"] >= 2 else 3 if c["frost_rank"] >= 1 else 0
        elif wmin <= 6:
            city_s += 3 if c["frost_rank"] >= 1 else 0
        if "coastal" in (city.get("climate_type") or "") and c["salt"]:
            city_s += 3
        city_s = min(city_s, 10.0)
        if city_s >= 5:
            reasons.append("Well-suited to %s's climate" % city.get("key", "").title())
        if wmin <= 2 and c["frost_rank"] == 0:
            warnings.append("May need winter protection in %s" % city.get("key", "").title())
        if smax >= 40 and c["heat_rank"] == 0:
            warnings.append("Wants shade during %s's peak summer" % city.get("key", "").title())

    total = water_s + sun_s + space_s + exp_s + purpose_s + prio_s + city_s
    score = round(total * 100.0 / 110.0)
    return score, {"reasons": reasons[:4], "warnings": warnings[:3], "exclude": None}


def _verdict(score: int) -> str:
    if score >= 80:
        return "excellent_match"
    if score >= 65:
        return "good_match"
    if score >= 45:
        return "risky"
    return "not_recommended"


def _label_for(c: dict) -> (str, str):
    if c["type"] == "flower":
        g = flower_service.all_groups().get(c["group"], {})
        return g.get("emoji", "🌸"), g.get("label", c["group"])
    return CATEGORY_EMOJI.get(c["category"], "🌱"), (c["category"] or "plant").replace("_", " ").title()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def normalize_answers(raw: dict) -> dict:
    """Validate + normalize the questionnaire payload. Raises ValueError."""
    raw = raw or {}

    def pick(key, valid, default):
        val = raw.get(key)
        if val in (None, ""):
            return default
        if val not in valid:
            raise ValueError("Invalid value for '%s': %s" % (key, val))
        return val

    purposes = raw.get("purposes") or []
    priorities = raw.get("priorities") or []
    if not isinstance(purposes, list) or not isinstance(priorities, list):
        raise ValueError("'purposes' and 'priorities' must be lists")
    for p in purposes:
        if p not in VALID_PURPOSES:
            raise ValueError("Unknown purpose: %s" % p)
    for p in priorities:
        if p not in VALID_PRIORITIES:
            raise ValueError("Unknown priority: %s" % p)

    return {
        "city": (raw.get("city") or "").strip(),
        "space": pick("space", VALID_SPACE, "balcony"),
        "sun": pick("sun", VALID_SUN, "unsure"),
        "water": pick("water", VALID_WATER, "sometimes"),
        "experience": pick("experience", VALID_EXPERIENCE, "some"),
        "pets": bool(raw.get("pets")),
        "purposes": purposes,
        "priorities": priorities,
    }


def recommend(raw_answers: dict) -> dict:
    ans = normalize_answers(raw_answers)
    city = city_info(ans["city"])

    pool = _candidate_pool()

    if ans["purposes"]:
        pool = [c for c in pool if any(_matches_purpose(c, p) for p in ans["purposes"])]

    results, avoid = [], []
    for c in pool:
        if ans["pets"] and not c["pet_safe"]:
            avoid.append((c, "Toxic to pets — not safe with animals at home"))
            continue

        space_reason = _space_block(c, ans["space"])
        if space_reason:
            avoid.append((c, space_reason))
            continue

        score, payload = _score(c, ans, city)
        if score is None:
            avoid.append((c, payload["exclude"]))
            continue

        emoji, label = _label_for(c)
        results.append({
            "id": c["id"], "type": c["type"], "name": c["name"],
            "scientific": c["scientific"], "local_name": c["local_name"],
            "plant_id": c["plant_id"], "emoji": emoji, "label": label,
            "group": c["group"], "category": c["category"],
            "water": c["water"], "sun": c["sun"], "difficulty": c["difficulty"],
            "bloom_months": c["bloom_months"],
            "score": score, "verdict": _verdict(score),
            "reasons": payload["reasons"], "warnings": payload["warnings"],
        })

    results.sort(key=lambda r: (-r["score"], r["name"]))

    # avoid list: dedupe by name, keep it short and readable
    seen, avoid_out = set(), []
    for c, reason in avoid:
        if c["name"].lower() in seen:
            continue
        seen.add(c["name"].lower())
        emoji, _ = _label_for(c)
        avoid_out.append({
            "id": c["id"], "type": c["type"], "name": c["name"],
            "emoji": emoji, "reason": reason,
        })
        if len(avoid_out) >= 8:
            break

    return {
        "answers": ans,
        "city": ({"key": city["key"], "summary": city.get("summary", "")} if city else None),
        "results": results[:12],
        "avoid": avoid_out,
        "counts": {
            "considered": len(pool),
            "returned": min(len(results), 12),
            "excluded": len(avoid_out),
        },
    }


def plan_context(answers: dict, recommendation: dict) -> str:
    """Compact, factual context block for the optional AI garden plan."""
    ans = recommendation.get("answers") or answers
    lines = [
        "Gardener profile:",
        "- City: %s" % (ans.get("city") or "not given"),
        "- Space: %s" % ans.get("space"),
        "- Direct sun: %s" % ans.get("sun"),
        "- Watering capacity: %s" % ans.get("water"),
        "- Experience: %s" % ans.get("experience"),
        "- Pets at home: %s" % ("yes" if ans.get("pets") else "no"),
        "- Wanted: %s" % (", ".join(ans.get("purposes")) or "anything"),
        "- Priorities: %s" % (", ".join(ans.get("priorities")) or "none stated"),
    ]
    if recommendation.get("city"):
        lines.append("- Local climate: %s" % recommendation["city"].get("summary", ""))
    lines.append("")
    lines.append("Engine output (deterministic matching - trust these facts):")
    for r in recommendation.get("results", [])[:6]:
        lines.append("- %s (score %d/100, %s): %s" % (
            r["name"], r["score"], r["verdict"],
            "; ".join(r["reasons"]) or "good general fit"))
    if recommendation.get("avoid"):
        lines.append("Plants the engine excluded and why:")
        for a in recommendation["avoid"][:5]:
            lines.append("- %s: %s" % (a["name"], a["reason"]))
    return "\n".join(lines)
