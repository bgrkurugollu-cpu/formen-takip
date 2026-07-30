from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Formen Performans Takip Sistemi"
    environment: str = "development"
    debug: bool = True

    database_url: str = "postgresql+psycopg://formen:formen@localhost:5432/formen_takip"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    max_failed_login_attempts: int = 5
    account_lockout_minutes: int = 15

    timezone: str = "Europe/Istanbul"

    cors_origins: list[str] = ["http://localhost:5173"]

    sap_base_url: str | None = None
    sap_client_id: str | None = None
    sap_client_secret: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
