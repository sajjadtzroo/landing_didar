"""Single-admin auth: argon2 password hash + itsdangerous signed session cookie.

Run `python -m app.core.security <password>` to generate a hash for ADMIN_PASSWORD_HASH.
"""

import sys

from itsdangerous import BadSignature, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.core.config import settings

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")
SESSION_COOKIE = "didar_admin"


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
    except (BadSignature, Exception):  # noqa: BLE001 — any decode failure = no session
        return None
    return data.get("sub")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m app.core.security <password>")
        raise SystemExit(1)
    print(hash_password(sys.argv[1]))
