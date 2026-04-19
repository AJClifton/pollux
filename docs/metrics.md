# Prometheus Metrics

The service exposes Prometheus metrics at `GET /metrics` on the same port as the API (8000). All metrics are prefixed `pollux_`.

## Metrics

### HTTP (default, from `prometheus-flask-exporter`)

- `pollux_http_request_total{method, status, endpoint}`
- `pollux_http_request_duration_seconds{method, status, endpoint}` — histogram, buckets `5ms–10s`
- `pollux_http_request_exceptions_total`

Health endpoints (`/health/live`, `/health/ready`) are excluded via `@metrics.do_not_track()`.

### Cache (Redis)

- `pollux_cache_hits_total{key_prefix}`
- `pollux_cache_misses_total{key_prefix}`
- `pollux_redis_errors_total{operation}` — distinguishes Redis outages from true cache misses

`key_prefix` is a bounded label: `forecast_hourly`, `forecast_daily`, `geocode`, or `other`.

### Database

- `pollux_db_query_duration_seconds{query}` — histogram, buckets `1ms–500ms`
- `pollux_db_pool_size`, `pollux_db_pool_checked_out`, `pollux_db_pool_overflow` — SQLAlchemy pool gauges (aggregated `livesum` across workers)

### External API

- `pollux_external_api_duration_seconds{provider}` — histogram, success-only, buckets `25ms–10s`
- `pollux_external_api_errors_total{provider, reason}` — `reason` ∈ `timeout | connection | http_5xx | http_4xx | other`

### Readiness / coalescer / build

- `pollux_readiness_failures_total{dependency}` — `dependency` ∈ `redis | database`
- `pollux_coalescer_in_flight{coalescer}`, `pollux_coalescer_waits_total{coalescer}`
- `pollux_build_info{version, commit_sha}` — gauge, always `1`

## Kubernetes configuration

### Required: tmpfs volume for multiprocess metric files

`prometheus-flask-exporter` runs `prometheus_client` in multiprocess mode under Gunicorn (4 workers). Workers write mmap'd `.db` files to `$PROMETHEUS_MULTIPROC_DIR` (default `/tmp/prometheus_multiproc`). Under load this is hot I/O — mount it as tmpfs, not the default disk-backed `emptyDir`:

```yaml
spec:
  template:
    spec:
      containers:
        - name: pollux-data-service
          env:
            - name: APP_VERSION
              value: "1.2.3"
            - name: GIT_COMMIT
              value: "abc1234"
          volumeMounts:
            - name: prom-multiproc
              mountPath: /tmp/prometheus_multiproc
      volumes:
        - name: prom-multiproc
          emptyDir:
            medium: Memory
            sizeLimit: 64Mi
```

### Scraping

Either a Prometheus Operator `ServiceMonitor`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: pollux-data-service
spec:
  selector:
    matchLabels:
      app: pollux-data-service
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

Or plain-Prometheus pod annotations:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

Scrape interval **≥30s** — aggregation cost scales linearly with scrapers.

## Grafana query rule

Quantiles are not linearly aggregable. Always `sum by (<label>, le)` across `pod`/`instance` **before** calling `histogram_quantile`:

```promql
histogram_quantile(
  0.95,
  sum by (provider, le) (
    rate(pollux_external_api_duration_seconds_bucket[5m])
  )
)
```

## Adding new metrics

New DB query or API provider = one-line call-site change, no new metric definition:

```python
from app.core.metrics import db_query_duration_seconds, observe, time_external_api

with observe(db_query_duration_seconds, query="forecast_weekly_lookup"):
    ...

PROVIDER = "met_office"
with time_external_api(PROVIDER):
    resp = requests.get(...)
```

### Cardinality rules (enforced at review)

- Label values must come from a fixed, enumerated set — module-level string constants, never request data, user input, URLs with params, IDs, or timestamps.
- If a new dependency needs a materially different bucket range (e.g. multi-minute batch jobs vs sub-10ms queries), add a new histogram rather than overloading an existing one — a histogram shares one bucket set across all label values.
- `test_metricsCardinality_underThreshold()` in `tests/test_metrics.py` is an automated guardrail against accidental high-cardinality labels.
