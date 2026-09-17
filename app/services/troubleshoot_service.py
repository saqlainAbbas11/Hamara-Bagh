import json
import os

_RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "troubleshoot_rules.json")
_rules_cache = None


def _load_rules():
    global _rules_cache
    if _rules_cache is None:
        with open(_RULES_PATH, "r", encoding="utf-8") as f:
            _rules_cache = json.load(f)
    return _rules_cache


def list_symptoms():
    return [{"symptom_key": r["symptom_key"], "symptom_label": r["symptom_label"]} for r in _load_rules()]


def diagnose(symptom_keys: list):
    """Given a list of selected symptom keys, return matched rule details,
    with causes ranked by likelihood.
    """
    rules = _load_rules()
    selected = [r for r in rules if r["symptom_key"] in symptom_keys]

    if not selected:
        return {"matched": False, "results": []}

    likelihood_rank = {"high": 0, "medium": 1, "low": 2}
    results = []
    for rule in selected:
        causes = sorted(rule["causes"], key=lambda c: likelihood_rank.get(c["likelihood"], 3))
        results.append({
            "symptom_key": rule["symptom_key"],
            "symptom_label": rule["symptom_label"],
            "causes": causes,
        })

    return {"matched": True, "results": results}
