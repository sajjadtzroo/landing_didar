#!/usr/bin/env bash
# Concurrency sweep with ab -> CSV on stdout.
# Usage: ab_sweep.sh <url> <total-requests> [label] [concurrency list...]
# CSV: label,concurrency,rps,p50_ms,p95_ms,p99_ms,failed,non2xx
set -euo pipefail
URL="$1"; N="$2"; LABEL="${3:-run}"; shift 3 || true
CONCS=("${@:-1 2 4 8 16 32 64 128 256}")
[ $# -eq 0 ] && CONCS=(1 2 4 8 16 32 64 128 256)

echo "label,c,rps,p50,p95,p99,failed,non2xx"
for c in "${CONCS[@]}"; do
  out=$(ab -n "$N" -c "$c" -k -s 30 -q "$URL" 2>/dev/null)
  rps=$(echo "$out" | awk '/Requests per second/{print $4}')
  p50=$(echo "$out" | awk '/  50%/{print $2}')
  p95=$(echo "$out" | awk '/  95%/{print $2}')
  p99=$(echo "$out" | awk '/  99%/{print $2}')
  failed=$(echo "$out" | awk '/Failed requests/{print $3}')
  non2xx=$(echo "$out" | awk '/Non-2xx responses/{print $3}')
  echo "$LABEL,$c,$rps,$p50,$p95,$p99,${failed:-0},${non2xx:-0}"
done
