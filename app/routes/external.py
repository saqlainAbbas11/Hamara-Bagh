from flask import Blueprint, jsonify, request

from app.services import ai_service, perenual_service, taxonomy_service, wikipedia_service, trefle_service

bp = Blueprint("external", __name__, url_prefix="/api/external")


@bp.route("/status", methods=["GET"])
def status():
    """Tells the frontend (and you) which external sources are actually
    usable right now, given configured API keys. Useful for debugging and
    for showing an honest 'data sources' page.
    """
    return jsonify({
        "perenual": {
            "enabled": perenual_service.is_enabled(),
            "note": "Free tier: ~100 requests/day, full care data only for ~first 3000 species IDs.",
        },
        "trefle": {
            "enabled": trefle_service.is_enabled(),
            "note": "Historically unreliable/has had extended outages - treated as best-effort only.",
        },
        "gbif": {"enabled": True, "note": "Free, no key required, institutional uptime."},
        "inaturalist": {"enabled": True, "note": "Free, no key required."},
        "wikipedia": {"enabled": True, "note": "Free, no key required."},
        "huggingface": {
            "enabled": ai_service.is_enabled(),
            "note": "Optional free token - adds AI answers to the /troubleshoot page.",
        },
        "open_meteo": {"enabled": True, "note": "Free, no key required. Powers weather + air quality."},
    })


@bp.route("/perenual/search", methods=["GET"])
def perenual_search():
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    if not q:
        return jsonify({"error": "Provide ?q="}), 400
    return jsonify(perenual_service.search_species(q, page))


@bp.route("/gbif/match", methods=["GET"])
def gbif_match():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "Provide ?q="}), 400
    return jsonify(taxonomy_service.gbif_species_match(q))


@bp.route("/inaturalist/search", methods=["GET"])
def inaturalist_search():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "Provide ?q="}), 400
    return jsonify(taxonomy_service.inaturalist_taxa_search(q))


@bp.route("/wikipedia/summary", methods=["GET"])
def wikipedia_summary():
    title = request.args.get("title", "")
    if not title:
        return jsonify({"error": "Provide ?title="}), 400
    return jsonify(wikipedia_service.get_summary(title))


@bp.route("/trefle/search", methods=["GET"])
def trefle_search():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "Provide ?q="}), 400
    return jsonify(trefle_service.search_plants(q))
