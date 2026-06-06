from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str | None = None
    supabase_key: str | None = None
    auth_jwt_secret: str = "change-me"
    auth_access_token_minutes: int = 30
    auth_refresh_token_days: int = 14

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
