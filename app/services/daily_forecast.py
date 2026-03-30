from flask import current_app

from app.services import redis_service
from app.services.forecast_provider import ForecastProvider
from app.services.open_meteo_client import OpenMeteoClient


class DailyForecast:

    def __init__(self, lat, lon):
        self.lat = round(lat, 2)
        self.lon = round(lon, 2)
        self._data = self._load()

    def _load(self):
        """Fetch daily forecast with fallback: Redis -> Database -> Open-Meteo API."""
        cache_key = f"forecast:daily:{self.lat}:{self.lon}"
        if cached := redis_service.cache_get(cache_key):
            return cached

        redis_ttl = current_app.config["FORECAST_CACHE_TTL"]
        db_ttl = current_app.config["DB_FORECAST_CACHE_TTL"]
        result = ForecastProvider(OpenMeteoClient()).get_daily(self.lat, self.lon, db_ttl)
        redis_service.cache_set(cache_key, result, redis_ttl)
        return result

    def to_dict(self):
        return self._data
