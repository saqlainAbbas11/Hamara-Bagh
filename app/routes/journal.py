import os
import time
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request

from app.extensions import db
from app.models import Plant, UserPlantLog
from app.services import care_calculator, weather_service

bp = Blueprint("journal", __name__, url_prefix="/api/journal")

ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}


def _utcnow():
    return datetime.now(timezone.utc)


def _as_aware(dt):
    """SQLite drops timezone info on storage - treat naive timestamps as UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _client_id_from_request():
    """Accept the client id from ?client_id=, a JSON body, or a form field
    (the photo upload endpoint uses multipart form data)."""
    client_id = (request.args.get("client_id") or "").strip()
    if not client_id and request.form:
        client_id = (request.form.get("client_id") or "").strip()
    if not client_id:
        body = request.get_json(silent=True) or {}
        client_id = (body.get("client_id") or "").strip()
    return client_id or None


def _get_owned_entry(entry_id):
    """Fetch an entry and verify the caller owns it (same client_id).
    Without this check, anyone who guessed an id could edit someone else's
    journal - ids are small sequential integers, so guessing is trivial.

    Returns (entry, None) on success or (None, (json_response, status)).
    """
    entry = db.session.get(UserPlantLog, entry_id)
    if entry is None:
        return None, (jsonify({"error": f"No journal entry with id {entry_id}"}), 404)
    client_id = _client_id_from_request()
    if not client_id:
        return None, (jsonify({"error": "client_id is required"}), 400)
    if entry.client_id != client_id:
        return None, (jsonify({"error": "client_id does not match this journal entry"}), 403)
    return entry, None


@bp.route("", methods=["GET"])
def list_entries():
    client_id = _client_id_from_request()
    if not client_id:
        return jsonify({"error": "Provide ?client_id=... (generate/store one in the browser)."}), 400
    entries = UserPlantLog.query.filter_by(client_id=client_id).order_by(UserPlantLog.created_at.desc()).all()
    return jsonify({"count": len(entries), "results": [e.to_dict() for e in entries]})


@bp.route("", methods=["POST"])
def create_entry():
    body = request.get_json(silent=True) or {}
    client_id = (body.get("client_id") or "").strip()
    if not client_id:
        return jsonify({"error": "client_id is required"}), 400

    plant_id = body.get("plant_id")
    if plant_id is not None:
        if not isinstance(plant_id, int) or db.session.get(Plant, plant_id) is None:
            return jsonify({"error": "plant_id must reference a plant in the local dataset"}), 400

    entry = UserPlantLog(
        client_id=client_id,
        plant_id=plant_id,
        nickname=body.get("nickname"),
        city=body.get("city"),
        notes=body.get("notes"),
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201


@bp.route("/<int:entry_id>/watered", methods=["POST"])
def mark_watered(entry_id):
    entry, error = _get_owned_entry(entry_id)
    if error:
        return error
    entry.last_watered_at = _utcnow()
    db.session.commit()
    return jsonify(entry.to_dict())


@bp.route("/<int:entry_id>", methods=["DELETE"])
def delete_entry(entry_id):
    entry, error = _get_owned_entry(entry_id)
    if error:
        return error
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"deleted": True})


@bp.route("/reminders", methods=["GET"])
def reminders():
    """Watering reminders for one journal: combines each entry's species,
    its city's live climate, and when it was last watered into a plain
    "overdue / due now / upcoming" status. This is the data layer for future
    push/email notifications (see README roadmap).
    """
    client_id = _client_id_from_request()
    if not client_id:
        return jsonify({"error": "Provide ?client_id=..."}), 400

    entries = UserPlantLog.query.filter_by(client_id=client_id).order_by(UserPlantLog.created_at).all()

    now = _utcnow()
    city_snapshots = {}  # one weather lookup per distinct city, not per entry
    results = []
    for entry in entries:
        plant = db.session.get(Plant, entry.plant_id) if entry.plant_id else None

        snapshot = None
        if entry.city:
            city_key = entry.city.strip().lower()
            if city_key not in city_snapshots:
                geo = weather_service.geocode_city(entry.city)
                city_snapshots[city_key] = (
                    weather_service.get_climate_snapshot(geo["lat"], geo["lon"])
                    if geo and geo.get("found") else None
                )
            snapshot = city_snapshots[city_key]

        watering = care_calculator.estimate_watering_interval(plant, snapshot)
        interval_days = watering["interval_days"]

        last_watered = _as_aware(entry.last_watered_at) or _as_aware(entry.created_at) or now
        days_since = (now - last_watered).total_seconds() / 86400
        due_in_days = interval_days - days_since

        if due_in_days < -0.5:
            status = "overdue"
        elif due_in_days <= 0.5:
            status = "due_now"
        else:
            status = "upcoming"

        results.append({
            "entry": entry.to_dict(),
            "interval_days": interval_days,
            "days_since_watered": round(days_since, 1),
            "due_in_days": round(due_in_days, 1),
            "status": status,
            "note": watering["note"],
        })

    urgency_rank = {"overdue": 0, "due_now": 1, "upcoming": 2}
    results.sort(key=lambda r: (urgency_rank[r["status"]], r["due_in_days"]))

    return jsonify({
        "count": len(results),
        "needs_water_now": sum(1 for r in results if r["status"] in ("overdue", "due_now")),
        "reminders": results,
    })


@bp.route("/<int:entry_id>/photo", methods=["POST"])
def upload_photo(entry_id):
    """Attach a progress photo (multipart form field 'photo'; jpg/jpeg/png/
    webp/gif, max 6 MB - enforced by MAX_CONTENT_LENGTH). Files are stored
    under instance/uploads and served from /uploads/<filename>.
    """
    entry, error = _get_owned_entry(entry_id)
    if error:
        return error

    file = request.files.get("photo")
    if file is None or not file.filename:
        return jsonify({"error": "Attach an image in the 'photo' form field"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        return jsonify({"error": f"Unsupported image type - allowed: {sorted(ALLOWED_PHOTO_EXTENSIONS)}"}), 400

    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    filename = f"journal_{entry.id}_{int(time.time())}.{ext}"
    file.save(os.path.join(folder, filename))

    entry.photo_url = f"/uploads/{filename}"
    db.session.commit()
    return jsonify(entry.to_dict())
