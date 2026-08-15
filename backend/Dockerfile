# Stage 1: build wheels (needs build-essential for packages without wheels).
FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: runtime — no compiler toolchain, smaller image + surface.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# Aggregate Prometheus metrics across gunicorn workers (mmap files live here).
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY . .
RUN chmod +x entrypoint.sh \
    && useradd -m -u 1000 app \
    && mkdir -p /app/media /tmp/prometheus \
    && chown -R app:app /app /tmp/prometheus
USER app

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", "-w", "2", "--timeout", "60", "--graceful-timeout", "30"]
