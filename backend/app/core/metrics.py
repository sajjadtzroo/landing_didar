"""Prometheus metrics. Works under gunicorn -w N via prometheus_client's
multiprocess mode when PROMETHEUS_MULTIPROC_DIR is set (each worker writes
mmap files there; /metrics aggregates across workers). Without the env var it
degrades to single-process mode — fine for dev and tests.

Labels use the ROUTE TEMPLATE (/api/v1/products/{slug}), never the raw path,
so cardinality stays bounded.
"""

import os

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests",
    ["method", "route", "status"],
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
RATELIMIT_TRIPS = Counter(
    "ratelimit_trips_total", "Requests rejected by the rate limiter", ["route"]
)
SLOW_QUERIES = Counter("db_slow_queries_total", "Queries above SLOW_QUERY_MS")


def metrics_endpoint() -> Response:
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        from prometheus_client import CollectorRegistry, multiprocess

        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        payload = generate_latest(registry)
    else:
        payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
