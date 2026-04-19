"""Prometheus metric definitions and timing helpers.

Leaf module: imports only stdlib and prometheus libs. Must not import from
app.services.* or other app modules — keeps the import graph acyclic as
services add metrics.
"""
import os
import time
from contextlib import contextmanager

import requests
from prometheus_client import Counter, Gauge, Histogram
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics

_HTTP_BUCKETS = (.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10)
_DB_BUCKETS = (.001, .0025, .005, .01, .025, .05, .1, .25, .5)
_API_BUCKETS = (.025, .05, .1, .25, .5, 1, 2, 5, 10)

metrics = GunicornInternalPrometheusMetrics.for_app_factory(
    defaults_prefix="pollux",
    group_by="endpoint",
    buckets=_HTTP_BUCKETS,
)

cache_hits_total = Counter(
    "pollux_cache_hits_total", "Redis cache hits", ["key_prefix"]
)
cache_misses_total = Counter(
    "pollux_cache_misses_total", "Redis cache misses", ["key_prefix"]
)
redis_errors_total = Counter(
    "pollux_redis_errors_total", "Redis client errors (not misses)", ["operation"]
)

db_query_duration_seconds = Histogram(
    "pollux_db_query_duration_seconds",
    "Database query duration in seconds",
    ["query"],
    buckets=_DB_BUCKETS,
)

external_api_duration_seconds = Histogram(
    "pollux_external_api_duration_seconds",
    "External API call duration in seconds (successful calls only)",
    ["provider"],
    buckets=_API_BUCKETS,
)
external_api_errors_total = Counter(
    "pollux_external_api_errors_total",
    "External API call errors",
    ["provider", "reason"],
)

readiness_failures_total = Counter(
    "pollux_readiness_failures_total",
    "Readiness probe failures by dependency",
    ["dependency"],
)

db_pool_size = Gauge(
    "pollux_db_pool_size", "SQLAlchemy pool size",
    multiprocess_mode="livesum",
)
db_pool_checked_out = Gauge(
    "pollux_db_pool_checked_out", "Connections currently checked out",
    multiprocess_mode="livesum",
)
db_pool_overflow = Gauge(
    "pollux_db_pool_overflow", "Overflow connections in use",
    multiprocess_mode="livesum",
)

coalescer_in_flight = Gauge(
    "pollux_coalescer_in_flight", "Coalesced calls currently in flight",
    ["coalescer"],
    multiprocess_mode="livesum",
)
coalescer_waits_total = Counter(
    "pollux_coalescer_waits_total",
    "Number of coalesced waiters (callers that joined an in-flight call)",
    ["coalescer"],
)

build_info = Gauge(
    "pollux_build_info", "Service build information",
    ["version", "commit_sha"],
    multiprocess_mode="max",
)
build_info.labels(
    version=os.environ.get("APP_VERSION", "dev"),
    commit_sha=os.environ.get("GIT_COMMIT", "unknown"),
).set(1)


@contextmanager
def observe(histogram, **labels):
    """Time a block and record to the given histogram."""
    with histogram.labels(**labels).time():
        yield


def _classify_api_error(exc):
    """Map an exception to a low-cardinality reason label."""
    if isinstance(exc, requests.exceptions.Timeout):
        return "timeout"
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "connection"
    if isinstance(exc, requests.exceptions.HTTPError):
        code = getattr(exc.response, "status_code", 0) or 0
        if 500 <= code < 600:
            return "http_5xx"
        if 400 <= code < 500:
            return "http_4xx"
    return "other"


@contextmanager
def time_external_api(provider):
    """Time an external API call. Records latency only on success; on failure
    bumps the error counter (labelled by reason) and re-raises."""
    start = time.perf_counter()
    try:
        yield
    except Exception as exc:
        external_api_errors_total.labels(
            provider=provider, reason=_classify_api_error(exc)
        ).inc()
        raise
    else:
        external_api_duration_seconds.labels(provider=provider).observe(
            time.perf_counter() - start
        )
