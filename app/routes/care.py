from flask import Blueprint, jsonify, request

from app.models import Plant
from app.services import ai_service, care_calculator, weather_service, troubleshoot_service

bp = Blueprint("care", __name__, url_prefix="/api/care")


@bp.route("/watering/<int:plant_id>", methods=["GET"])
def watering(plant_id):
    """Watering interval for a specific plant, optionally adjusted for a
    location's current climate (?city=Karachi or ?lat=..&lon=..).
    """
    plant = Plant.query.get_or_404(plant_id)

    snapshot = None
    city = request.args.get("city")
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)

    if lat is not None and lon is not None:
        snapshot = weather_service.get_climate_snapshot(lat, lon)
    elif city:
        geo = weather_service.geocode_city(city)
        if geo and geo.get("found"):
            snapshot = weather_service.get_climate_snapshot(geo["lat"], geo["lon"])

    result = care_calculator.estimate_watering_interval(plant, snapshot)
    return jsonify({"plant": plant.to_dict(), "watering": result})


@bp.route("/troubleshoot/symptoms", methods=["GET"])
def symptoms():
    return jsonify({"symptoms": troubleshoot_service.list_symptoms()})


@bp.route("/troubleshoot/diagnose", methods=["POST"])
def diagnose():
    """Body: {"symptoms": ["yellow_leaves", "wilting_despite_watering"]}"""
    body = request.get_json(silent=True) or {}
    symptom_keys = body.get("symptoms", [])
    if not isinstance(symptom_keys, list) or not symptom_keys:
        return jsonify({"error": "Provide a non-empty 'symptoms' list."}), 400

    result = troubleshoot_service.diagnose(symptom_keys)
    return jsonify(result)


@bp.route("/troubleshoot/ask", methods=["POST"])
def troubleshoot_ask():
    """Answers a free-text question with the optional AI plant doctor.

    Body: {"question": "...", "plant": "tomato", "symptoms": ["yellow_leaves"]}
    Ticked symptoms are resolved server-side and sent to the model as hints
    alongside the rules engine's top causes. Needs HUGGINGFACE_API_TOKEN.
    """
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Type a question for the AI plant doctor first."}), 400
    question = question[:600]

    plant = (body.get("plant") or "").strip()[:80] or None

    labels, causes = [], []
    symptom_keys = body.get("symptoms", [])
    if isinstance(symptom_keys, list) and symptom_keys:
        for item in troubleshoot_service.diagnose(symptom_keys).get("results", []):
            labels.append(item.get("symptom_label", ""))
            for cause in (item.get("causes") or [])[:3]:
                causes.append(cause.get("cause", ""))

    try:
        result = ai_service.ask_ai(question, plant=plant, symptoms=labels, causes=causes)
    except ai_service.AIUnavailable:
        return jsonify({
            "error": "The AI plant doctor needs a free Hugging Face token. "
                     "Add HUGGINGFACE_API_TOKEN to .env and restart the app."
        }), 503
    except ai_service.AIServiceError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(result)
