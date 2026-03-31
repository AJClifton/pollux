import os


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    FORECAST_CACHE_TTL = int(os.getenv("FORECAST_CACHE_TTL", 900))
    DB_FORECAST_CACHE_TTL = int(os.getenv("DB_FORECAST_CACHE_TTL", 3600))
    GEOCODE_CACHE_TTL = int(os.getenv("GEOCODE_CACHE_TTL", 86400))
    OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://pollux:pollux@localhost:5432/pollux"
    )


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    REDIS_URL = "redis://localhost:6379/1"


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
