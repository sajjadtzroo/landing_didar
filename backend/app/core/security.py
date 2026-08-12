"""Single-admin auth: argon2 password hash + itsdangerous signed session cookie.

Run `python -m app.core.security <password>` to generate a hash for ADMIN_PASSWORD_HASH.
"""

import asyncio
import sys

from itsdangerous import URLSafeTimedSerializer
from passlib.context import CryptContext

from app.core.config import settings

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")
SESSION_COOKIE = "didar_admin"
CUSTOMER_COOKIE = "didar_customer"


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    return _pwd.verify(password, hashed)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="admin-session")


def issue_session(username: str) -> str:
    return _serializer().dumps({"sub": username})


def read_session(token: str | None) -> str | None:
    """Return the username if the signed cookie is valid and unexpired, else None."""
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=settings.session_max_age)
    except Exception:  # noqa: BLE001 — any decode failure = no session
        return None
    return data.get("sub")


# --- Customer session (same signing scheme, different salt so the two cookie
# families can't be swapped) + OTP hashing (argon2, reusing the password ctx) ---
def _customer_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="customer-session")


def issue_customer_session(customer_id: str) -> str:
    return _customer_serializer().dumps({"sub": customer_id})


def read_customer_session(token: str | None) -> str | None:
    """Return the customer id if the signed cookie is valid and unexpired."""
    if not token:
        return None
    try:
        data = _customer_serializer().loads(token, max_age=settings.session_max_age)
    except Exception:  # noqa: BLE001 — any decode failure = no session
        return None
    return data.get("sub")


def hash_otp(code: str) -> str:
    return _pwd.hash(code)


def verify_otp(code: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return _pwd.verify(code, hashed)
    except Exception:  # noqa: BLE001 — malformed hash = no match
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m app.core.security <password>")
        raise SystemExit(1)
    print(hash_password(sys.argv[1]))


async def hash_password_async(password: str) -> str:
    """Argon2 is ~100ms of CPU — never run it on the event loop."""
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(password: str, hashed: str) -> bool:
    return await asyncio.to_thread(verify_password, password, hashed)


async def hash_otp_async(code: str) -> str:
    return await asyncio.to_thread(hash_otp, code)


async def verify_otp_async(code: str, hashed: str) -> bool:
    return await asyncio.to_thread(verify_otp, code, hashed)


def get_client_ip(request) -> str | None:
    """Real client IP behind a proxy — X-Forwarded-For's first hop is the client.
    Lives here (not in a router layer) because rate-limit keys, scan logging and
    order IP-hashing all depend on it."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None
