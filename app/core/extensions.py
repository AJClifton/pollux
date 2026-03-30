from datetime import datetime, timezone

import redis
from flask_sqlalchemy import SQLAlchemy


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime for consistent DB storage across SQLite and PostgreSQL."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


db = SQLAlchemy()
redis_client = None


def init_redis(app):
    global redis_client
    redis_client = redis.from_url(app.config["REDIS_URL"], decode_responses=True)
