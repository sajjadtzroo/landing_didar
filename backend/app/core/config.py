from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://didar:didar@localhost:5432/didar"

    # Logging (loguru sink level)
    log_level: str = "INFO"

    # Auth / session (single admin account, no user table)
    admin_username: str = "admin"
    admin_password_hash: str = ""  # argon2 hash; generate with `python -m app.core.security`
    secret_key: str = "change-me-in-prod"  # signs the session cookie
    session_max_age: int = 60 * 60 * 24 * 7  # 7 days
    cookie_secure: bool = False  # True in production (HTTPS)

    # CORS — the Nuxt origin(s), comma-separated
    frontend_origin: str = "http://localhost:3000"

    # Media storage
    media_root: str = "media"
    media_url_prefix: str = "/media"

    # SMS notification (primary). Kavenegar-style HTTP by default; provider-swappable.
    sms_provider: str = "kavenegar"  # kavenegar | log
    sms_api_key: str = ""
    sms_sender: str = ""
    sms_admin_phone: str = ""  # where new-order alerts go
    admin_order_base_url: str = "http://localhost:3000/admin/orders"

    # Telegram / Email stubs (unused unless you switch the primary adapter)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
