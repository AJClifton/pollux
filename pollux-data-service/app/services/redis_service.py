import json
import logging

from app.core.extensions import redis_client
from app.core.metrics import cache_hits_total, cache_misses_total, redis_errors_total

logger = logging.getLogger(__name__)


def cache_get(prefix, key):
    """Get parsed JSON from Redis. Returns None on miss or error."""
    full_key = f"{prefix}:{key}"
    label = prefix.replace(":", "_")
    try:
        value = redis_client.get(full_key)
    except Exception:
        logger.warning("Redis read failed for key=%s", full_key, exc_info=True)
        redis_errors_total.labels(operation="get").inc()
        return None

    if value:
        cache_hits_total.labels(key_prefix=label).inc()
        return json.loads(value)

    cache_misses_total.labels(key_prefix=label).inc()
    return None


def cache_set(prefix, key, data, ttl):
    """Set JSON in Redis with TTL. Silently fails on error."""
    full_key = f"{prefix}:{key}"
    try:
        redis_client.setex(full_key, ttl, json.dumps(data))
    except Exception:
        logger.warning("Redis write failed for key=%s", full_key, exc_info=True)
        redis_errors_total.labels(operation="set").inc()
