#!/usr/bin/env python
"""Concurrent login (OTP request + verify) stress sweep.

Each virtual user runs the full flow: POST /otp/request (unique phone +
unique X-Forwarded-For, so the 5/hour rate limit keys per-user like real
traffic), read dev_code from the response, POST /otp/verify, check the
session cookie. Needs a backend where dev_code is revealed (local dev).

Usage: stress_login.py [base_url] [level ...]
       stress_login.py http://localhost:8001 10 25 50 100 200
"""

import asyncio
import statistics
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
LEVELS = [int(a) for a in sys.argv[2:]] or [10, 25, 50, 100, 200]
API = "/api/v1/account"


async def login_flow(client: httpx.AsyncClient, uid: int) -> float:
    """One full login; returns latency in seconds. Raises on any failure."""
    phone = f"091{uid:08d}"
    headers = {"X-Forwarded-For": f"10.{(uid >> 16) & 255}.{(uid >> 8) & 255}.{uid & 255}"}
    t0 = time.perf_counter()
    r = await client.post(f"{API}/otp/request", json={"phone": phone}, headers=headers)
    r.raise_for_status()
    code = r.json()["dev_code"]
    assert code, "dev_code hidden — run against a dev backend, not production"
    r = await client.post(
        f"{API}/otp/verify", json={"phone": phone, "code": code}, headers=headers
    )
    r.raise_for_status()
    assert "didar_customer" in r.headers.get("set-cookie", ""), "no session cookie"
    return time.perf_counter() - t0


async def run_level(n: int, uid_base: int) -> dict:
    async with httpx.AsyncClient(base_url=BASE, timeout=60) as client:
        t0 = time.perf_counter()
        results = await asyncio.gather(
            *(login_flow(client, uid_base + i) for i in range(n)),
            return_exceptions=True,
        )
        wall = time.perf_counter() - t0
    ok = [r for r in results if isinstance(r, float)]
    errors = [r for r in results if not isinstance(r, float)]
    return {
        "n": n,
        "ok": len(ok),
        "wall": wall,
        "rate": len(ok) / wall,
        "p50": statistics.median(ok) if ok else 0,
        "p95": statistics.quantiles(ok, n=20)[-1] if len(ok) >= 20 else max(ok, default=0),
        "err": str(errors[0])[:60] if errors else "",
    }


async def main() -> int:
    print(f"target: {BASE}  (full login = otp/request + otp/verify)")
    print(f"{'users':>6} {'ok':>6} {'wall_s':>7} {'login/s':>8} {'p50_s':>6} {'p95_s':>6}  first_error")
    uid_base = int(time.time()) % 100_000_000  # unique phones per run
    failed = False
    for n in LEVELS:
        r = await run_level(n, uid_base)
        uid_base += n
        print(
            f"{r['n']:>6} {r['ok']:>6} {r['wall']:>7.1f} {r['rate']:>8.1f}"
            f" {r['p50']:>6.2f} {r['p95']:>6.2f}  {r['err']}"
        )
        if r["ok"] < r["n"]:
            failed = True
    return 1 if failed and LEVELS and LEVELS[0] > 0 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
