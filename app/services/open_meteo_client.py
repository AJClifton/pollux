from datetime import datetime

import requests
from flask import current_app

from app.core.extensions import utcnow
from app.core.metrics import time_external_api

PROVIDER = "open_meteo"

HOURLY_FIELD_MAP = {
    "temperature_2m": "temperature",
    "dewpoint_2m": "dewpoint",
    "rain": "rain",
    "cloud_cover": "cloud_cover_total",
    "cloud_cover_low": "cloud_cover_low",
    "cloud_cover_mid": "cloud_cover_mid",
    "cloud_cover_high": "cloud_cover_high",
    "visibility": "visibility",
    "surface_pressure": "surface_pressure",
    "wind_speed_10m": "wind_speed",
    "wind_direction_10m": "wind_direction",
    "wind_gusts_10m": "wind_gusts",
}

DAILY_FIELD_MAP = {
    "weather_code": "weather_code",
    "temperature_2m_max": "maximum_temperature",
    "temperature_2m_min": "minimum_temperature",
    "precipitation_sum": "precipitation_sum",
    "precipitation_probability_max": "precipitation_probability_max",
    "wind_speed_10m_max": "maximum_wind_speed",
    "sunrise": "sunrise",
    "sunset": "sunset",
}


class OpenMeteoClient:

    def fetch_forecast(self, lat, lon):
        """Fetch hourly and daily forecast from Open-Meteo. Raises on HTTP errors."""
        url = current_app.config["OPEN_METEO_FORECAST_URL"]
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(HOURLY_FIELD_MAP.keys()),
            "daily": ",".join(DAILY_FIELD_MAP.keys()),
        }
        with time_external_api(PROVIDER):
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()

    def fetch_geocode(self, name):
        """Fetch geocoding results from Open-Meteo. Raises on HTTP errors."""
        url = current_app.config["OPEN_METEO_GEOCODING_URL"]
        params = {"name": name, "count": 5, "language": "en"}
        with time_external_api(PROVIDER):
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()

    def parse_forecast(self, lat, lon, api_data):
        """Parse Open-Meteo response into hourly and daily row dicts."""
        now = utcnow()
        hourly_rows = self._build_rows(
            lat, lon, api_data.get("hourly", {}),
            HOURLY_FIELD_MAP, lambda t: datetime.fromisoformat(t), "datetime", now,
        )
        daily_rows = self._build_rows(
            lat, lon, api_data.get("daily", {}),
            DAILY_FIELD_MAP, lambda t: datetime.fromisoformat(t).date(), "date", now,
        )
        return hourly_rows, daily_rows

    def _build_rows(self, lat, lon, section, field_map, parse_time, time_key, now):
        """Parse an API response section into a list of row dicts."""
        parsed_times = [parse_time(t) for t in section.get("time", [])]
        if not parsed_times:
            return []

        rows = []
        for i, t in enumerate(parsed_times):
            row_data = {"latitude": lat, "longitude": lon, time_key: t, "fetched_at": now}
            for api_field, model_field in field_map.items():
                row_data[model_field] = section.get(api_field, [None])[i]
            rows.append(row_data)
        return rows
