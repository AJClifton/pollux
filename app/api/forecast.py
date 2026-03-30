from datetime import date, timedelta
from flask import Blueprint, jsonify, request

from app.services import geocoding_service
from app.services.daily_forecast import DailyForecast
from app.services.hourly_forecast import HourlyForecast

forecast_bp = Blueprint("forecast", __name__)


class ApiError(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code


def _resolve_lat_lon():
    """Extract and return (lat, lon) from request args, or raise ApiError."""
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    location = request.args.get("location", type=str)

    if lat is not None and lon is not None:
        return lat, lon
    elif location:
        results = geocoding_service.get_coordinates(location)
        if not results:
            raise ApiError(f"No results found for '{location}'", 404)
        return results[0]["latitude"], results[0]["longitude"]
    else:
        raise ApiError("Provide lat/lon or location parameter", 400)


@forecast_bp.route("/forecast/hourly")
def get_hourly_forecast():
    try:
        lat, lon = _resolve_lat_lon()

        date_str = request.args.get("date", type=str)
        if not date_str:
            raise ApiError("date parameter is required (YYYY-MM-DD)", 400)
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            raise ApiError("date must be in YYYY-MM-DD format", 400)

        if target_date > date.today() + timedelta(days=6):
            raise ApiError("date must be within 6 days from today", 400)

        forecast = HourlyForecast(lat, lon, target_date)
    except ApiError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to fetch forecast: {e}"}), 502

    return jsonify(forecast.to_dict())


@forecast_bp.route("/forecast/daily")
def get_daily_forecast():
    try:
        lat, lon = _resolve_lat_lon()
        forecast = DailyForecast(lat, lon)
    except ApiError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to fetch forecast: {e}"}), 502

    return jsonify(forecast.to_dict())
