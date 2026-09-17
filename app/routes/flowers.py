from flask import Blueprint, jsonify

from app.services import flower_service

bp = Blueprint("flowers", __name__, url_prefix="/api/flowers")


@bp.route("", methods=["GET"])
def list_flowers():
    """Full ornamental catalog in one response (~100KB). The /flowers page
    filters/searches client-side so every interaction is instant; the
    matchmaker reads the same entries server-side via flower_service.
    """
    catalog = flower_service.load_catalog()
    return jsonify({
        "total": len(catalog["flowers"]),
        "note": catalog.get("note"),
        "groups": catalog["groups"],
        "flowers": catalog["flowers"],
    })


@bp.route("/<slug>", methods=["GET"])
def get_flower(slug):
    flower = flower_service.by_slug(slug)
    if flower is None:
        return jsonify({"error": "Flower not found"}), 404
    return jsonify(flower)
