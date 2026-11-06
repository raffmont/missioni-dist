from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "postgresql+psycopg://missioni:change-me@db:5432/missioni"
    session_hours: int = 8
    retention_days: int = 365
    cookie_secure: bool = False
    allowed_origins: str = "http://localhost:5173"
    object_store_endpoint: str = "http://minio:9000"
    object_store_bucket: str = "missioni-private"
    object_store_access_key: str = ""
    object_store_secret_key: str = ""
    object_store_region: str = "us-east-1"
    local_storage_path: str = "storage/missioni-private"
    max_upload_bytes: int = 15_000_000
    max_pdf_pages: int = 30
    bank_match_date_tolerance_days: int = 14
    openai_extraction_enabled: bool = False
    openai_data_processing_authorized: bool = False
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    database_url_file: str | None = None
    object_store_access_key_file: str | None = None
    object_store_secret_key_file: str | None = None

    @model_validator(mode="after")
    def load_secret_files(self):
        """Load production secrets from mounted, root-managed files."""
        for value_name, file_name in (
            ("database_url", "database_url_file"),
            ("object_store_access_key", "object_store_access_key_file"),
            ("object_store_secret_key", "object_store_secret_key_file"),
        ):
            secret_path = getattr(self, file_name)
            if secret_path:
                value = Path(secret_path).read_text(encoding="utf-8").strip()
                if not value:
                    raise ValueError(f"{file_name} points to an empty file")
                setattr(self, value_name, value)
        if self.environment == "production":
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
            if self.openai_extraction_enabled or self.openai_data_processing_authorized:
                raise ValueError("external AI processing is disabled in production")
            if not self.object_store_access_key or not self.object_store_secret_key:
                raise ValueError("production object-store credentials are required")
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
