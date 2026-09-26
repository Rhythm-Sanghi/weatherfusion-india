from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
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
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:5180", "http://127.0.0.1:5180"]
    )
    verification_provider: str = "mock"
    verification_model_artifact_path: Path | None = None
    verification_ml_minimum_margin: float = Field(default=0.0, ge=0)
    geospatial_provider: str = "mock"
    log_level: str = "INFO"
    weather_connector_enabled: bool = True
    demo_mode: bool = False
    weather_api_base_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_connector_timeout_seconds: int = 8
    weather_cache_max_age_minutes: int = 1440
    weather_default_location_name: str = "Indore"
    weather_default_latitude: float = Field(default=22.7196, ge=-90, le=90)
    weather_default_longitude: float = Field(default=75.8577, ge=-180, le=180)
    weather_timezone: str = "Asia/Kolkata"
    weather_forecast_days: int = Field(default=2, ge=1, le=16)
    evidence_source_reliability_weight: float = Field(default=0.25, ge=0, le=1)
    evidence_independent_corroboration_weight: float = Field(default=0.25, ge=0, le=1)
    evidence_official_observation_weight: float = Field(default=0.20, ge=0, le=1)
    evidence_location_time_weight: float = Field(default=0.15, ge=0, le=1)
    evidence_validated_ml_weight: float = Field(default=0.15, ge=0, le=1)
    evidence_minimum_coverage: float = Field(default=0.60, ge=0, le=1)
    evidence_corroboration_radius_meters: int = Field(default=20_000, ge=1, le=100_000)
    evidence_corroboration_window_hours: int = Field(default=24, ge=1, le=168)
    evidence_corroboration_sources_for_full_support: int = Field(default=2, ge=1, le=10)
    evidence_location_time_max_age_hours: int = Field(default=720, ge=1, le=8760)
    evidence_location_time_future_tolerance_minutes: int = Field(default=120, ge=0, le=1440)

    @model_validator(mode="after")
    def evidence_weights_total_one(self) -> "Settings":
        total = (
            self.evidence_source_reliability_weight
            + self.evidence_independent_corroboration_weight
            + self.evidence_official_observation_weight
            + self.evidence_location_time_weight
            + self.evidence_validated_ml_weight
        )
        if abs(total - 1.0) > 0.000001:
            raise ValueError("Evidence weights must sum to 1.0.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
