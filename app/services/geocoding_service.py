from flask import current_app

from app.services import redis_service
from app.services.open_meteo_client import OpenMeteoClient
from app.services.request_coalescer import geocode_coalescer


def get_coordinates(name):
    """Resolve place name to coordinates. Redis -> Open-Meteo Geocoding API."""
    normalized = name.lower().strip()
    ttl = current_app.config["GEOCODE_CACHE_TTL"]

    cached = redis_service.cache_get("geocode", normalized)
    if cached:
        return cached

    client = OpenMeteoClient()
    data = geocode_coalescer.execute(f"geocode:{normalized}", client.fetch_geocode, name)

    results = _parse_results(data)
    redis_service.cache_set("geocode", normalized, results, ttl)
    return results


def _parse_results(data):
    """Extract relevant fields from Open-Meteo geocoding response."""
    raw_results = data.get("results", [])
    return [
        {
            "name": r.get("name"),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "country": r.get("country"),
            "admin1": r.get("admin1"),
        }
        for r in raw_results
    ]
