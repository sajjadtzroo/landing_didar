#!/usr/bin/env sh
set -e

echo "Waiting for database..."
python - <<'PY'
import asyncio, os, sys
import asyncpg

url = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
async def wait():
    for _ in range(30):
        try:
            conn = await asyncpg.connect(url)
            await conn.close()
            return
        except Exception:
            await asyncio.sleep(1)
    print("database not reachable", file=sys.stderr); sys.exit(1)
asyncio.run(wait())
PY

# Dev convenience: if no hash is set but a plaintext ADMIN_PASSWORD is, hash it
# at boot so `docker-compose up` gives a working admin login. In prod, set
# ADMIN_PASSWORD_HASH directly and leave ADMIN_PASSWORD unset.
if [ -z "$ADMIN_PASSWORD_HASH" ] && [ -n "$ADMIN_PASSWORD" ]; then
  echo "Hashing ADMIN_PASSWORD (dev bootstrap)..."
  ADMIN_PASSWORD_HASH=$(python -m app.core.security "$ADMIN_PASSWORD")
  export ADMIN_PASSWORD_HASH
fi

# Stale metric files from dead workers would double-count after a restart.
if [ -n "$PROMETHEUS_MULTIPROC_DIR" ]; then
  mkdir -p "$PROMETHEUS_MULTIPROC_DIR" && rm -f "$PROMETHEUS_MULTIPROC_DIR"/*.db
fi

# Migrations/seed do NOT run here: with multiple workers/replicas an
# entrypoint-side `alembic upgrade` races itself. The one-shot `migrate`
# compose service owns them; backend waits on its completion (compose
# `service_completed_successfully`).

echo "Starting..."
exec "$@"
