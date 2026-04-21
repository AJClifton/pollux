from app.api.forecast import forecast_bp
from app.api.geocoding import geocoding_bp
from app.api.health import health_bp


def register_blueprints(app):
    app.register_blueprint(forecast_bp, url_prefix="/api")
    app.register_blueprint(geocoding_bp, url_prefix="/api")
    app.register_blueprint(health_bp)
