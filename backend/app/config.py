from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "postgresql+psycopg://missioni:change-me@db:5432/missioni"
    session_hours: int = 8
    retention_days: int = 365
    cookie_secure: bool = False
    allowed_origins: str = "http://localhost:5173"


@lru_cache
def settings() -> Settings:
    return Settings()
