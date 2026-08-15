"""Cross-domain validation + privacy helpers."""

import hashlib

# Iranian mobile number (orders, customer OTP, warranty/buyback forms).
PHONE_RE = r"^09\d{9}$"


def hash_ip(ip: str | None) -> str | None:
    """Store a one-way hash instead of the raw client IP (abuse tracing without
    keeping PII). Used by orders and serial-scan logging."""
    if not ip:
        return None
    return hashlib.sha256(ip.encode()).hexdigest()


def csv_safe(value: object) -> object:
    """Neutralize spreadsheet formula injection in exported cells: a leading
    = + - @ makes Excel execute the cell when the admin opens our CSV."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value
