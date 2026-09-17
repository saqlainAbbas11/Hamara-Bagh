"""Business logic for the crowdsourced community layer - the "this worked /
didn't work for me in [city]" reports that no existing API provides.
"""
from sqlalchemy import func

from app.extensions import db
from app.models import PlantReport

OUTCOMES = ("thrived", "struggled", "died")


def normalize_city(city: str) -> str:
    return (city or "").strip().lower()


def outcome_summary(plant_id: int, city: str = None) -> dict:
    """Count thrived/struggled/died reports for a plant, optionally limited
    to one city. 'confidence' reflects how much signal actually exists, so
    the frontend can avoid presenting 1 report as a verdict.
    """
    query = db.session.query(PlantReport.outcome, func.count(PlantReport.id))
    query = query.filter(PlantReport.plant_id == plant_id)
    if city:
        query = query.filter(PlantReport.city_key == normalize_city(city))

    counts = {outcome: 0 for outcome in OUTCOMES}
    for outcome, n in query.group_by(PlantReport.outcome).all():
        if outcome in counts:
            counts[outcome] = n

    total = sum(counts.values())
    if total >= 10:
        confidence = "high"
    elif total >= 3:
        confidence = "medium"
    elif total >= 1:
        confidence = "low"
    else:
        confidence = "none"

    return {"total": total, "counts": counts, "confidence": confidence}


def list_reports(plant_id=None, city=None, outcome=None, limit=50):
    query = PlantReport.query
    if plant_id is not None:
        query = query.filter(PlantReport.plant_id == plant_id)
    if city:
        query = query.filter(PlantReport.city_key == normalize_city(city))
    if outcome:
        query = query.filter(PlantReport.outcome == outcome)
    rows = query.order_by(PlantReport.created_at.desc()).limit(limit).all()
    return [r.to_dict() for r in rows]


def create_report(client_id, plant_id, city, outcome, duration_months=None, notes=None):
    """Persist one report (validation happens in the route layer where the
    raw request body is available)."""
    report = PlantReport(
        client_id=client_id,
        plant_id=plant_id,
        city=city.strip(),
        city_key=normalize_city(city),
        outcome=outcome,
        duration_months=duration_months,
        notes=notes,
    )
    db.session.add(report)
    db.session.commit()
    return report
