"""Open-Meteo current-weather connector with an explicit local cache fallback."""
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from app.core.config import Settings
from app.domain.events import EventCategory

LOCATIONS = (("Mumbai", "Maharashtra", 19.076, 72.8777), ("Guwahati", "Assam", 26.1445, 91.7362), ("Jaipur", "Rajasthan", 26.9124, 75.7873))
CODE_MAP = {45: EventCategory.FOG, 48: EventCategory.FOG, 95: EventCategory.THUNDERSTORM, 96: EventCategory.THUNDERSTORM, 99: EventCategory.THUNDERSTORM}


@dataclass(frozen=True)
class ConnectorResult:
    records: list[dict]
    mode: str
    fetched_at: datetime


@dataclass(frozen=True)
class ForecastResult:
    payload: dict
    mode: str
    fetched_at: datetime


class OpenMeteoConnector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cache_path = Path(__file__).resolve().parents[4] / ".weather_cache" / "open_meteo.json"
        self.forecast_cache_path = Path(__file__).resolve().parents[4] / ".weather_cache" / "open_meteo_forecast.json"

    async def fetch_forecast(self) -> ForecastResult:
        params = {
            "latitude": self.settings.weather_default_latitude,
            "longitude": self.settings.weather_default_longitude,
            "current": "temperature_2m,relative_humidity_2m,rain,precipitation,weather_code,wind_speed_10m",
            "hourly": "temperature_2m,relative_humidity_2m,rain,precipitation,precipitation_probability,weather_code,wind_speed_10m",
            "timezone": self.settings.weather_timezone,
            "forecast_days": self.settings.weather_forecast_days,
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.weather_connector_timeout_seconds) as client:
                response = await client.get(self.settings.weather_api_base_url, params=params)
                response.raise_for_status()
                payload = response.json()
            if not isinstance(payload.get("current"), dict) or not isinstance(payload.get("hourly"), dict):
                raise ValueError("Malformed Open-Meteo forecast response")
            fetched_at = datetime.now(UTC)
            self._write_json_cache(self.forecast_cache_path, payload, fetched_at)
            return ForecastResult(payload, "live", fetched_at)
        except (httpx.HTTPError, ValueError) as exc:
            cached = self._read_json_cache(self.forecast_cache_path)
            if cached is None:
                raise RuntimeError("Open-Meteo forecast is unavailable and no valid cached response exists.") from exc
            return ForecastResult(cached["payload"], "cached", datetime.fromisoformat(cached["fetched_at"]))

    async def fetch(self) -> ConnectorResult:
        try:
            records = []
            async with httpx.AsyncClient(timeout=self.settings.weather_connector_timeout_seconds) as client:
                for city, state, latitude, longitude in LOCATIONS:
                    response = await client.get(self.settings.weather_api_base_url, params={"latitude": latitude, "longitude": longitude, "current_weather": "true", "timezone": "UTC"})
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload.get("current_weather"), dict):
                        raise ValueError("Malformed Open-Meteo current_weather response")
                    records.append({"city": city, "state": state, "latitude": latitude, "longitude": longitude, "payload": payload})
            self._write_cache(records)
            return ConnectorResult(records, "live", datetime.now(UTC))
        except (httpx.HTTPError, ValueError) as exc:
            cached = self._read_cache()
            if cached is None:
                raise RuntimeError("Open-Meteo is unavailable and no valid cached response exists.") from exc
            return ConnectorResult(cached["records"], "cached", datetime.fromisoformat(cached["fetched_at"]))

    def _write_cache(self, records: list[dict]) -> None:
        self._write_json_cache(self.cache_path, {"records": records}, datetime.now(UTC))

    def _read_cache(self) -> dict | None:
        cached = self._read_json_cache(self.cache_path)
        if cached is None:
            try:
                legacy = json.loads(self.cache_path.read_text(encoding="utf-8"))
                if datetime.now(UTC) - datetime.fromisoformat(legacy["fetched_at"]) > timedelta(minutes=self.settings.weather_cache_max_age_minutes):
                    return None
                return legacy if isinstance(legacy.get("records"), list) else None
            except (OSError, ValueError, KeyError):
                return None
        return {"records": cached["payload"].get("records"), "fetched_at": cached["fetched_at"]}

    def _write_json_cache(self, path: Path, payload: dict, fetched_at: datetime) -> None:
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"fetched_at": fetched_at.isoformat(), "payload": payload}), encoding="utf-8")

    def _read_json_cache(self, path: Path) -> dict | None:
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if datetime.now(UTC) - datetime.fromisoformat(cached["fetched_at"]) > timedelta(minutes=self.settings.weather_cache_max_age_minutes):
                return None
            return cached if isinstance(cached.get("payload"), dict) else None
        except (OSError, ValueError, KeyError):
            return None

    @staticmethod
    def normalize(record: dict, mode: str, retrieved_at: datetime | None = None) -> dict:
        current = record["payload"]["current_weather"]
        code = int(current["weathercode"])
        event_type = CODE_MAP.get(code, EventCategory.HEAVY_RAINFALL if current.get("precipitation", 0) > 0 else EventCategory.STRONG_WIND if abs(current.get("windspeed", 0)) >= 35 else EventCategory.UNKNOWN)
        severity = "HIGH" if abs(current.get("windspeed", 0)) >= 50 else "MODERATE" if event_type != EventCategory.UNKNOWN else "LOW"
        observed = current["time"].replace("Z", "+00:00")
        external_id = f"open-meteo:{record['city'].lower()}:{observed}"
        metadata = {
            "origin_mode": "OPEN_METEO_LIVE" if mode == "live" else "OPEN_METEO_CACHED",
            "source_provider": "Open-Meteo",
            "source_reference": "https://open-meteo.com/",
            "connector_version": "1.0",
            "weather_code": code,
            "observation_time": observed,
        }
        if retrieved_at is not None:
            metadata["retrieved_at"] = retrieved_at.astimezone(UTC).isoformat()
        if mode == "cached" and retrieved_at is not None:
            metadata["cache_age_seconds"] = max(
                0, round((datetime.now(UTC) - retrieved_at.astimezone(UTC)).total_seconds())
            )
        return {"source": "Open-Meteo Current Weather", "source_type": "EXTERNAL_WEATHER", "external_id": external_id, "event_type": event_type, "severity": severity, "title": f"Open-Meteo observation for {record['city']}", "description": f"Weather code {code}; wind speed {current.get('windspeed')} km/h.", "raw_text": json.dumps(record["payload"]), "latitude": record["latitude"], "longitude": record["longitude"], "state": record["state"], "city": record["city"], "observed_at": observed, "metadata": metadata}
