from flask import Blueprint, jsonify, request

from app.models import Plant
from app.services import community_service, perenual_service, taxonomy_service, wikipedia_service
from app.utils import int_arg

bp = Blueprint("plants", __name__, url_prefix="/api/plants")


@bp.route("", methods=["GET"])
def list_plants():
    """List/search local plant dataset with optional filters.
    Query params: q, category, difficulty, sunlight, water_need, max_results
    """
    query = Plant.query

    q = request.args.get("q")
    if q:
        like = f"%{q}%"
        query = query.filter(Plant.common_name.ilike(like) | Plant.scientific_name.ilike(like))

    for field in ("category", "difficulty", "sunlight", "water_need", "season"):
        val = request.args.get(field)
        if val:
            query = query.filter(getattr(Plant, field) == val)

    limit = int_arg("max_results", 50, minimum=1, maximum=200)
    plants = query.limit(limit).all()
    return jsonify({"count": len(plants), "results": [p.to_dict() for p in plants]})


@bp.route("/<int:plant_id>", methods=["GET"])
def get_plant(plant_id):
    """Full plant detail. Optionally enrich with external sources via
    ?enrich=1 (adds a Wikipedia summary + GBIF taxonomy lookup - both free,
    no key needed, cached so repeat views are instant).
    """
    plant = Plant.query.get_or_404(plant_id)
    data = plant.to_dict()

    if request.args.get("community") == "1":
        city = request.args.get("city")
        data["community"] = {
            "city": city,
            "summary": community_service.outcome_summary(plant_id, city),
        }

    if request.args.get("enrich") == "1":
        data["external"] = {}
        try:
            data["external"]["wikipedia"] = wikipedia_service.get_summary(plant.common_name)
        except Exception as exc:  # noqa: BLE001 - never let an enrichment failure break the response
            data["external"]["wikipedia"] = {"found": False, "error": str(exc)}

        try:
            data["external"]["gbif"] = taxonomy_service.gbif_species_match(plant.scientific_name or plant.common_name)
        except Exception as exc:  # noqa: BLE001
            data["external"]["gbif"] = {"error": str(exc)}

    return jsonify(data)


@bp.route("/categories", methods=["GET"])
def list_categories():
    rows = Plant.query.with_entities(Plant.category).distinct().all()
    return jsonify({"categories": sorted({r[0] for r in rows if r[0]})})
