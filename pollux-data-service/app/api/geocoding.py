from flask import Blueprint, jsonify, request

from app.services import geocoding_service

geocoding_bp = Blueprint("geocoding", __name__)


@geocoding_bp.route("/geocode")
def get_geocode():
    name = request.args.get("name", type=str)
    if not name:
        return jsonify({"error": "Provide a name parameter"}), 400

    try:
        results = geocoding_service.get_coordinates(name)
    except Exception as e:
        return jsonify({"error": f"Failed to geocode: {e}"}), 502

    return jsonify({"results": results})
