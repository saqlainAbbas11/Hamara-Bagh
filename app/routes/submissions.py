"""Backend for the "suggest a plant" form: users propose plants, which land
in a review queue instead of going straight into the curated dataset.
"""
from flask import Blueprint, current_app, jsonify, request

from app.extensions import db
from app.models import PlantSubmission
from app.utils import int_arg

bp = Blueprint("submissions", __name__, url_prefix="/api/submissions")

VALID_STATUSES = ("pending", "approved", "rejected")


def _require_admin():
    """Gate the review endpoints behind ADMIN_TOKEN when it's configured.
    Local dev (no token set) stays open so the flow can be tried immediately.

    Returns None when allowed, or a (response, status) tuple when blocked.
    """
    token = current_app.config.get("ADMIN_TOKEN")
    if not token:
        return None
    provided = request.headers.get("X-Admin-Token") or request.args.get("admin_token")
    if provided != token:
        return jsonify({"error": "A valid admin token is required for this operation."}), 403
    return None


@bp.route("", methods=["POST"])
def create_submission():
    """Anyone can suggest a plant.
    Body: {"common_name": "...", "scientific_name": "...", "category": "...",
           "city": "...", "notes": "...", "client_id": "..."}
    """
    body = request.get_json(silent=True) or {}
    common_name = (body.get("common_name") or "").strip()
    if not common_name:
        return jsonify({"error": "common_name is required"}), 400
    if len(common_name) > 120:
        return jsonify({"error": "common_name must be 120 characters or fewer"}), 400

    notes = (body.get("notes") or "").strip() or None
    if notes and len(notes) > 2000:
        return jsonify({"error": "notes must be 2000 characters or fewer"}), 400

    submission = PlantSubmission(
        client_id=(body.get("client_id") or "").strip() or None,
        common_name=common_name,
        scientific_name=(body.get("scientific_name") or "").strip() or None,
        category=(body.get("category") or "").strip() or None,
        city=(body.get("city") or "").strip() or None,
        notes=notes,
    )
    db.session.add(submission)
    db.session.commit()
    return jsonify(submission.to_dict()), 201


@bp.route("", methods=["GET"])
def list_submissions():
    """Review queue. ?status=pending|approved|rejected (default pending)."""
    error = _require_admin()
    if error:
        return error

    status = request.args.get("status", "pending")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {list(VALID_STATUSES)}"}), 400

    limit = int_arg("limit", 50, minimum=1, maximum=200)
    rows = (PlantSubmission.query.filter_by(status=status)
            .order_by(PlantSubmission.created_at.desc()).limit(limit).all())
    return jsonify({"count": len(rows), "status": status, "results": [r.to_dict() for r in rows]})


@bp.route("/<int:submission_id>/review", methods=["POST"])
def review_submission(submission_id):
    """Mark a submission approved or rejected (approval here only flags it;
    a maintainer still merges the plant into data/plants.json, then re-seeds).
    Body: {"status": "approved"|"rejected"}
    """
    error = _require_admin()
    if error:
        return error

    submission = db.session.get(PlantSubmission, submission_id)
    if submission is None:
        return jsonify({"error": f"No submission with id {submission_id}"}), 404

    body = request.get_json(silent=True) or {}
    status = (body.get("status") or "").strip().lower()
    if status not in ("approved", "rejected"):
        return jsonify({"error": "status must be 'approved' or 'rejected'"}), 400

    submission.status = status
    db.session.commit()
    return jsonify(submission.to_dict())
