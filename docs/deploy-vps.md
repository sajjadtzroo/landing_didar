# VPS Deployment — CI/CD with a self-hosted GitHub runner

Everything ships from this repo; the pipeline is **inert until you set the repo
variable `DEPLOY_ENABLED=true`** (Settings → Secrets and variables → Actions →
Variables). Until then `deploy.yml` skips both jobs, so nothing queues.

Architecture: push to `main` → backend test gate (ruff + import-linter + pytest,
reused from `backend.yml`) → the runner **on the VPS** builds the images locally
and rolls the compose stack. No image registry is involved — on Iranian networks
that's the difference between "works" and "fights sanctions".

```
GitHub (tests on GitHub-hosted runner)
   └─ deploy job → self-hosted runner on the VPS
        docker compose build && up -d      (built on the box)
        Caddy :80/:443 ── frontend:3000 / api → backend:8000
        Postgres + Redis (compose-internal only, no published ports)
```

## 1. One-time server prep (Ubuntu 22.04+, 2+ vCPU, 4 GB RAM)

```bash
# Docker + compose (needs compose >= 2.24 for `ports: !override`)
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER   # re-login after

# Iranian VPS: Docker Hub is blocked — set a registry mirror BEFORE first pull
cat > /etc/docker/daemon.json <<'EOF'
{ "registry-mirrors": ["https://docker.arvancloud.ir"] }
EOF
systemctl restart docker

# Firewall: web + SSH only (the compose override publishes nothing else)
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable

# 2 GB swap (builds are memory-hungry on small boxes)
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 2. Secrets file — `/opt/didar/.env`

```bash
mkdir -p /opt/didar && chmod 700 /opt/didar
cat > /opt/didar/.env <<'EOF'
DOMAIN=didargold.ir
POSTGRES_PASSWORD=<long random>
SECRET_KEY=<24+ random chars — cookie signing; app refuses weak values in prod>
ADMIN_PASSWORD_HASH=<from: python -m app.core.security "the-password">
# SMS (PayamSMS) — leave SMS_PROVIDER=log until creds exist
SMS_PROVIDER=payamsms
SMS_SENDER=98...
PAYAMSMS_SYSTEM_NAME=...
PAYAMSMS_USERNAME=...
PAYAMSMS_PASSWORD=...
PAYAMSMS_CLIENT_ID=...
PAYAMSMS_CLIENT_SECRET=...
SMS_ADMIN_PHONE=09...
# MinIO/S3 — keep using Liara's bucket, or leave empty for local-disk media
MINIO_ENDPOINT=storage.c2.liara.site
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_BUCKET=didargoldd
MINIO_SECURE=true
EOF
chmod 600 /opt/didar/.env
```

DNS: point `didargold.ir` and `api.didargold.ir` A-records at the VPS. Caddy
fetches TLS certificates automatically on first request.

## 3. Install the GitHub runner (label `didar-vps`)

Repo → Settings → Actions → Runners → **New self-hosted runner** (copy the
token from that page):

```bash
mkdir ~/actions-runner && cd ~/actions-runner
curl -o runner.tar.gz -L https://github.com/actions/runner/releases/latest/download/actions-runner-linux-x64-<ver>.tar.gz
tar xzf runner.tar.gz
./config.sh --url https://github.com/sajjadtzroo/landing_didar \
            --token <TOKEN> --labels didar-vps --unattended
sudo ./svc.sh install && sudo ./svc.sh start    # systemd service, survives reboots
```

The runner only makes **outbound** connections to GitHub — no inbound ports.

## 4. First deploy

```bash
# arm the pipeline
#   GitHub → Settings → ... → Variables → New: DEPLOY_ENABLED = true
# then either push to main, or Actions → deploy → Run workflow
```

First boot runs `alembic upgrade head` + idempotent seed automatically
(backend entrypoint). Verify: `https://api.<domain>/health` and `/ready`.

Manual fallback (no CI): on the server,
`git pull && docker compose -p didar -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/didar/.env up -d --build`.

## 5. Backups (the thing a VPS does NOT do for you)

```bash
cat > /etc/cron.daily/didar-pgdump <<'EOF'
#!/bin/sh
docker compose -p didar exec -T db pg_dump -U didar didar | gzip \
  > /opt/didar/backups/didar-$(date +%F).sql.gz
find /opt/didar/backups -name '*.sql.gz' -mtime +14 -delete
EOF
chmod +x /etc/cron.daily/didar-pgdump && mkdir -p /opt/didar/backups
```

Copy backups off-box (rclone to any S3/another server) — a backup on the same
disk is not a backup.

## 6. Rollback

Every deploy builds from the checked-out commit, so:
Actions → deploy → Run workflow on the previous good commit, **or** on the
server: `git checkout <sha>` + the manual command from §4. Migrations are
forward-only — a rollback that crosses a schema migration needs the matching
`alembic downgrade` first (rare; most of ours are additive).

## Known limits (accepted)

- ~5–10 s downtime per deploy (`compose up` recreates containers). Blue-green
  behind Caddy is the upgrade path if it ever matters.
- Runner executes CI-defined commands on the prod box — keep repo write access
  tight; the runner is only registered to this repo, jobs run only from `main`.
- `pg_stat_statements`, Grafana/Loki (the `didar-observability` compose) can be
  added on the same box later; ports stay internal.
