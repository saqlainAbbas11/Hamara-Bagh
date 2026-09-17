from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Plant, PlantReport
from app.services import community_service
from app.services.community_service import OUTCOMES
from app.utils import int_arg

bp = Blueprint("community", __name__, url_prefix="/api/community")


@bp.route("/reports", methods=["GET"])
def list_reports():
    """Browse community reports.
    Filters: ?plant_id=1&city=Karachi&outcome=thrived&limit=50
    """
    plant_id = request.args.get("plant_id", type=int)
    city = request.args.get("city")
    outcome = request.args.get("outcome")
    if outcome and outcome not in OUTCOMES:
        return jsonify({"error": f"outcome must be one of {list(OUTCOMES)}"}), 400

    limit = int_arg("limit", 50, minimum=1, maximum=200)
    reports = community_service.list_reports(plant_id, city, outcome, limit)
    return jsonify({"count": len(reports), "results": reports})


@bp.route("/reports", methods=["POST"])
def create_report():
    """Record "this worked / didn't work for me in [city]".
    Body: {"client_id": "...", "plant_id": 1, "city": "Karachi",
           "outcome": "thrived|struggled|died",
           "duration_months": 6, "notes": "..."}
    """
    body = request.get_json(silent=True) or {}

    client_id = (body.get("client_id") or "").strip()
    city = (body.get("city") or "").strip()
    outcome = (body.get("outcome") or "").strip().lower()
    plant_id = body.get("plant_id")

    if not client_id:
        return jsonify({"error": "client_id is required"}), 400
    if not city:
        return jsonify({"error": "city is required"}), 400
    if outcome not in OUTCOMES:
        return jsonify({"error": f"outcome must be one of {list(OUTCOMES)}"}), 400
    if not isinstance(plant_id, int) or db.session.get(Plant, plant_id) is None:
        return jsonify({"error": "plant_id must reference a plant in the local dataset"}), 400

    notes = (body.get("notes") or "").strip() or None
    if notes and len(notes) > 2000:
        return jsonify({"error": "notes must be 2000 characters or fewer"}), 400

    duration = body.get("duration_months")
    if duration is not None:
        try:
            duration = int(duration)
        except (TypeError, ValueError):
            return jsonify({"error": "duration_months must be a whole number"}), 400
        if duration < 0 or duration > 600:
            return jsonify({"error": "duration_months looks unreasonable"}), 400

    report = community_service.create_report(
        client_id=client_id, plant_id=plant_id, city=city,
        outcome=outcome, duration_months=duration, notes=notes,
    )
    return jsonify(report.to_dict()), 201


@bp.route("/reports/<int:report_id>/vote", methods=["POST"])
def vote(report_id):
    """Upvote a report - one vote per client, enforced server-side.
    Body (or ?client_id=): {"client_id": "..."}
    """
    body = request.get_json(silent=True) or {}
    client_id = (body.get("client_id") or request.args.get("client_id") or "").strip()
    if not client_id:
        return jsonify({"error": "client_id is required"}), 400

    report = db.session.get(PlantReport, report_id)
    if report is None:
        return jsonify({"error": f"No report with id {report_id}"}), 404

    counted = report.register_vote(client_id)
    db.session.commit()
    return jsonify({"counted": counted, "upvotes": report.upvotes})


@bp.route("/summary", methods=["GET"])
def summary():
    """Outcome counts for one plant: ?plant_id=1, optionally ?city=Karachi."""
    plant_id = request.args.get("plant_id", type=int)
    if not plant_id:
        return jsonify({"error": "Provide ?plant_id="}), 400

    city = request.args.get("city")
    return jsonify({
        "plant_id": plant_id,
        "city": city,
        "summary": community_service.outcome_summary(plant_id, city),
    })
