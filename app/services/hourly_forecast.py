from flask import current_app

from app.services import redis_service
from app.services.forecast_provider import ForecastProvider
from app.services.open_meteo_client import OpenMeteoClient


class HourlyForecast:

    def __init__(self, lat, lon, date):
        self.lat = round(lat, 2)
        self.lon = round(lon, 2)
        self.date = date
        self._data = self._load()

    def _load(self):
        """Fetch hourly forecast for the night of the given date (sunset to next-day sunrise +/-1h)."""
        cache_key = f"forecast:hourly:{self.lat}:{self.lon}:{self.date.isoformat()}"
        if cached := redis_service.cache_get(cache_key):
            return cached

        redis_ttl = current_app.config["FORECAST_CACHE_TTL"]
        db_ttl = current_app.config["DB_FORECAST_CACHE_TTL"]
        result = ForecastProvider(OpenMeteoClient()).get_hourly(self.lat, self.lon, self.date, db_ttl)
        redis_service.cache_set(cache_key, result, redis_ttl)
        return result

    def to_dict(self):
        return self._data
