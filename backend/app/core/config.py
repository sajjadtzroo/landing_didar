from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://didar:didar@localhost:5432/didar"

    # Redis (optional). Blank = in-process caches + per-worker rate limits (fine
    # single-node). Set to share cache/limits across workers/instances; the app
    # fails open if Redis is unreachable. e.g. redis://redis:6379/0
    redis_url: str = ""

    # Logging (loguru sink level)
    log_level: str = "INFO"
    # JSON logs for collectors (Loki/Alloy); false = human-readable dev output.
    log_json: bool = False
    # Per-module overrides, e.g. "db.query=DEBUG,api.auth=DEBUG" — everything
    # else stays at log_level. Namespaces come from get_logger(<module>).
    log_levels: str = ""
    log_service: str = "didar-api"  # `service` field on every record
    app_env: str = "dev"  # `env` field on every record (dev | production)
    # Queries slower than this are logged on the db.query namespace (0 = off).
    slow_query_ms: int = 200

    # Auth / session (single admin account, no user table)
    admin_username: str = "admin"
    admin_password_hash: str = ""  # argon2 hash; generate with `python -m app.core.security`
    secret_key: str = "change-me-in-prod"  # signs the session cookie
    session_max_age: int = 60 * 60 * 24 * 7  # 7 days
    cookie_secure: bool = False  # True in production (HTTPS)
    # "lax" for same-origin dev; "none" when the admin SPA and API are on
    # different sites (e.g. separate Liara subdomains). "none" REQUIRES secure=True.
    cookie_samesite: str = "lax"

    # CORS — the Nuxt origin(s), comma-separated
    frontend_origin: str = "http://localhost:3000"

    # Media storage
    media_root: str = "media"
    media_url_prefix: str = "/media"

    # MinIO / S3 — SOURCE for the product-photo import job only
    # (python -m app.import_images). Not touched at request time. Blank = disabled.
    minio_endpoint: str = ""  # host:port, e.g. "minio.example.com:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = ""
    minio_secure: bool = True  # https

    # SMS notification (primary). Kavenegar-style HTTP by default; provider-swappable.
    sms_provider: str = "kavenegar"  # kavenegar | log
    sms_api_key: str = ""
    sms_sender: str = ""
    sms_admin_phone: str = ""  # where new-order alerts go
    admin_order_base_url: str = "http://localhost:3000/admin/orders"

    # Test phones: OTP dev_code is returned (and the real SMS skipped) for these
    # even in production — for QA / app-review logins without a live gateway.
    otp_test_phones: str = ""  # comma-separated, e.g. "09028068820"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def otp_test_phone_set(self) -> set[str]:
        return {p.strip() for p in self.otp_test_phones.split(",") if p.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
