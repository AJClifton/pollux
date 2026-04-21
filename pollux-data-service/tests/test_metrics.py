import re

import pytest
import requests


def _scrape(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    return resp.data.decode("utf-8")


def _sample(body, metric, **labels):
    """Return the float value of a single metric sample, or 0.0 if not present."""
    label_str = ""
    if labels:
        parts = [f'{k}="{v}"' for k, v in labels.items()]
        label_str = "{" + ".*?".join(parts) + ".*?}"
    pattern = rf"^{re.escape(metric)}{label_str}\s+([0-9eE\.\+\-]+)\s*$"
    match = re.search(pattern, body, re.MULTILINE)
    return float(match.group(1)) if match else 0.0


def test_metricsEndpoint_returnsPrometheusFormat(client, mock_redis):
    # Arrange / Act
    resp = client.get("/metrics")

    # Assert
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/plain")
    body = resp.data.decode("utf-8")
    assert "pollux_build_info" in body


def test_cacheGet_hit_incrementsHitCounter(client, mock_redis):
    # Arrange
    from app.services import redis_service
    mock_redis.get.return_value = '{"x": 1}'
    before = _sample(_scrape(client), "pollux_cache_hits_total",
                     key_prefix="forecast_hourly")

    # Act
    redis_service.cache_get("forecast:hourly", "51.5:-0.1:2026-04-18")

    # Assert
    after = _sample(_scrape(client), "pollux_cache_hits_total",
                    key_prefix="forecast_hourly")
    assert after > before


def test_cacheGet_miss_incrementsMissCounter(client, mock_redis):
    # Arrange
    from app.services import redis_service
    mock_redis.get.return_value = None
    before = _sample(_scrape(client), "pollux_cache_misses_total",
                     key_prefix="forecast_daily")

    # Act
    redis_service.cache_get("forecast:daily", "51.5:-0.1")

    # Assert
    after = _sample(_scrape(client), "pollux_cache_misses_total",
                    key_prefix="forecast_daily")
    assert after > before


def test_cacheGet_redisError_incrementsRedisErrorCounterNotMiss(client, mock_redis):
    # Arrange
    from app.services import redis_service
    mock_redis.get.side_effect = Exception("boom")
    miss_before = _sample(_scrape(client), "pollux_cache_misses_total",
                          key_prefix="geocode")
    err_before = _sample(_scrape(client), "pollux_redis_errors_total",
                         operation="get")

    # Act
    result = redis_service.cache_get("geocode", "london")

    # Assert
    body = _scrape(client)
    assert result is None
    assert _sample(body, "pollux_redis_errors_total", operation="get") > err_before
    assert _sample(body, "pollux_cache_misses_total", key_prefix="geocode") == miss_before


def test_timeExternalApi_timeout_incrementsErrorWithTimeoutReason(client, mock_redis):
    # Arrange
    from app.core.metrics import time_external_api
    before = _sample(_scrape(client), "pollux_external_api_errors_total",
                     provider="open_meteo", reason="timeout")

    # Act
    with pytest.raises(requests.exceptions.Timeout):
        with time_external_api("open_meteo"):
            raise requests.exceptions.Timeout()

    # Assert
    after = _sample(_scrape(client), "pollux_external_api_errors_total",
                    provider="open_meteo", reason="timeout")
    assert after > before


def test_timeExternalApi_success_recordsLatency(client, mock_redis):
    # Arrange
    from app.core.metrics import time_external_api
    before = _sample(_scrape(client),
                     "pollux_external_api_duration_seconds_count",
                     provider="open_meteo")

    # Act
    with time_external_api("open_meteo"):
        pass

    # Assert
    after = _sample(_scrape(client),
                    "pollux_external_api_duration_seconds_count",
                    provider="open_meteo")
    assert after > before


def test_healthEndpoints_notTracked(client, mock_redis):
    # Arrange / Act
    client.get("/health/live")
    body = _scrape(client)

    # Assert
    assert 'endpoint="health.liveness"' not in body
    assert 'endpoint="health.readiness"' not in body


def test_metricsCardinality_underThreshold(client, mock_redis):
    # Arrange / Act
    body = _scrape(client)
    series = [
        line for line in body.splitlines()
        if line and not line.startswith("#")
    ]

    # Assert
    assert len(series) < 400, (
        f"Metric series count {len(series)} exceeds guardrail threshold. "
        f"Check recently added labels for unbounded cardinality."
    )
