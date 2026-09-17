from flask import Blueprint, jsonify, request

from app.services import ai_service, match_service

bp = Blueprint("match", __name__, url_prefix="/api/match")

GARDEN_PLAN_PROMPT = (
    "You are Hamara Bagh's garden planner — a friendly, practical master gardener "
    "writing for home gardeners in Pakistan. You receive a gardener's profile and "
    "a list of plants our matching engine scored for them. Trust those facts; do "
    "not invent plants outside the list except as brief companion suggestions. "
    "Write a short seasonal garden plan: a title line, then 4-7 numbered steps "
    "(what to plant first, where, watering rhythm, feeding, what to expect month "
    "by month). Name 3-5 specific plants from the list and why they suit this "
    "gardener. Keep every step to 1-2 sentences. Assume Pakistan's climate (45C "
    "summers, monsoon, northern frost). If pets are present, add one reminder "
    "about keeping toxic plants out of reach. Plain text only, no markdown "
    "symbols, no emojis."
)


@bp.route("/recommend", methods=["POST"])
def recommend():
    """Runs the questionnaire through the deterministic match engine.

    Body: {city, space, sun, water, experience, pets, purposes[], priorities[]}
    """
    body = request.get_json(silent=True) or {}
    try:
        result = match_service.recommend(body)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.route("/explain", methods=["POST"])
def explain():
    """Turns the engine's matches into an optional AI garden plan.

    The engine re-runs server-side so the model only ever sees sanitized,
    factual context. Needs HUGGINGFACE_API_TOKEN (same free token as the
    troubleshooter AI); without it the frontend hides this card entirely.
    """
    body = request.get_json(silent=True) or {}
    try:
        recommendation = match_service.recommend(body)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    context = match_service.plan_context(recommendation["answers"], recommendation)
    question = ("Write my personalised garden plan from my profile and the "
                "engine's matching results above.")

    try:
        result = ai_service.ask_ai(
            question, extra_context=context,
            system_prompt=GARDEN_PLAN_PROMPT, max_tokens=700,
        )
    except ai_service.AIUnavailable:
        return jsonify({
            "error": "The AI garden plan needs a free Hugging Face token. "
                     "Add HUGGINGFACE_API_TOKEN to .env and restart the app."
        }), 503
    except ai_service.AIServiceError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(result)
