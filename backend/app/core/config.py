from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Typed runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "WeatherFusion India API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+psycopg://weatherfusion:weatherfusion@localhost:55432/weatherfusion"
    )
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    verification_provider: str = "mock"
    geospatial_provider: str = "mock"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
