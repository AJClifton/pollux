import logging

from flask import Flask

from app.core.config import DevelopmentConfig
from app.core.extensions import db, init_redis
from app.core.metrics import (
    db_pool_checked_out, db_pool_overflow, db_pool_size, metrics,
)


logger = logging.getLogger(__name__)


def create_app(config_class=None):
    app = Flask(__name__)
    config_class = config_class or DevelopmentConfig
    app.config.from_object(config_class)

    db.init_app(app)
    init_redis(app)

    from app.api.routes import register_blueprints
    register_blueprints(app)

    metrics.init_app(app)

    @app.after_request
    def _update_pool_gauges(response):
        try:
            pool = db.engine.pool
            db_pool_size.set(pool.size())
            db_pool_checked_out.set(pool.checkedout())
            db_pool_overflow.set(pool.overflow())
        except Exception:
            logger.warning("Failed to update pool gauges", exc_info=True)
        return response

    with app.app_context():
        db.create_all()

    return app
