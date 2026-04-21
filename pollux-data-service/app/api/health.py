from flask import Blueprint, jsonify

from app.core.extensions import db, redis_client
from app.core.metrics import metrics, readiness_failures_total

health_bp = Blueprint("health", __name__)


@health_bp.route("/health/live")
@metrics.do_not_track()
def liveness():
    return jsonify({"status": "ok"})


@health_bp.route("/health/ready")
@metrics.do_not_track()
def readiness():
    errors = []

    try:
        redis_client.ping()
    except Exception:
        errors.append("redis")
        readiness_failures_total.labels(dependency="redis").inc()

    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception:
        errors.append("database")
        readiness_failures_total.labels(dependency="database").inc()

    if errors:
        return jsonify({"status": "unavailable", "errors": errors}), 503

    return jsonify({"status": "ready"})
