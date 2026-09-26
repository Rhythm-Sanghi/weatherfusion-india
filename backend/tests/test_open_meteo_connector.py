import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from app.core.config import Settings
from app.integrations.weather.open_meteo import OpenMeteoConnector


class Response:
    def __init__(self, payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload, self.error = payload, error
    def raise_for_status(self) -> None:
        if self.error:
            raise self.error
    def json(self) -> dict:
        if self.error:
            raise self.error
        return self.payload or {}


class Client:
    def __init__(self, response: Response, **_: object) -> None: self.response = response
    async def __aenter__(self): return self
    async def __aexit__(self, *_: object) -> None: return None
    async def get(self, *_: object, **__: object) -> Response: return self.response


def connector(tmp_path) -> OpenMeteoConnector:
    item = OpenMeteoConnector(Settings(database_url="sqlite://"))
    item.cache_path = tmp_path / "weather.json"
    return item


@pytest.mark.asyncio
async def test_live_fetch_normalizes_and_writes_cache(monkeypatch, tmp_path) -> None:
    payload = {"current_weather": {"weathercode": 95, "windspeed": 55, "time": "2026-09-19T06:00:00Z"}}
    monkeypatch.setattr("app.integrations.weather.open_meteo.httpx.AsyncClient", lambda **kwargs: Client(Response(payload)))
    item = connector(tmp_path)
    result = await item.fetch()
    normalized = item.normalize(result.records[0], result.mode, result.fetched_at)
    assert result.mode == "live" and len(result.records) == 3 and item.cache_path.exists()
    assert normalized["source"] == "Open-Meteo Current Weather"
    assert normalized["event_type"] == "THUNDERSTORM"
    assert normalized["metadata"]["origin_mode"] == "OPEN_METEO_LIVE"
    assert normalized["metadata"]["connector_version"] == "1.0"
    assert normalized["metadata"]["observation_time"] == "2026-09-19T06:00:00+00:00"
    assert normalized["metadata"]["retrieved_at"]


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [httpx.TimeoutException("timeout"), httpx.ConnectError("offline")])
async def test_transport_failures_use_cache(monkeypatch, tmp_path, error) -> None:
    item = connector(tmp_path)
    item.cache_path.write_text(json.dumps({"fetched_at": datetime.now(UTC).isoformat(), "records": [{"cached": True}]}))
    monkeypatch.setattr("app.integrations.weather.open_meteo.httpx.AsyncClient", lambda **kwargs: Client(Response(error=error)))
    result = await item.fetch()
    assert result.mode == "cached"
    normalized = item.normalize({"city": "Mumbai", "state": "Maharashtra", "latitude": 19.076, "longitude": 72.8777, "payload": {"current_weather": {"weathercode": 95, "windspeed": 55, "time": "2026-09-19T06:00:00Z"}}}, result.mode, result.fetched_at)
    assert normalized["metadata"]["origin_mode"] == "OPEN_METEO_CACHED"
    assert normalized["metadata"]["retrieved_at"]
    assert isinstance(normalized["metadata"]["cache_age_seconds"], int)


@pytest.mark.asyncio
async def test_http_malformed_and_expired_cache_are_unavailable(monkeypatch, tmp_path) -> None:
    item = connector(tmp_path)
    item.cache_path.write_text(json.dumps({"fetched_at": (datetime.now(UTC) - timedelta(days=2)).isoformat(), "records": [{"cached": True}]}))
    monkeypatch.setattr("app.integrations.weather.open_meteo.httpx.AsyncClient", lambda **kwargs: Client(Response({"unexpected": True})))
    with pytest.raises(RuntimeError, match="unavailable"):
        await item.fetch()


@pytest.mark.asyncio
async def test_forecast_requests_required_variables_and_preserves_cache_provenance(monkeypatch, tmp_path) -> None:
    payload = {
        "current": {"time": "2026-09-24T12:00", "temperature_2m": 28.5, "relative_humidity_2m": 62, "rain": 0, "precipitation": 0, "weather_code": 3, "wind_speed_10m": 12.4},
        "current_units": {"temperature_2m": "°C", "relative_humidity_2m": "%", "rain": "mm", "precipitation": "mm", "weather_code": "wmo code", "wind_speed_10m": "km/h"},
        "hourly": {"time": ["2026-09-24T12:00"], "temperature_2m": [28.5], "relative_humidity_2m": [62], "rain": [0], "precipitation": [0], "precipitation_probability": [5], "weather_code": [3], "wind_speed_10m": [12.4]},
    }
    captured: dict[str, object] = {}

    class ForecastClient(Client):
        async def get(self, _url: str, **kwargs: object) -> Response:
            captured.update(kwargs)
            return self.response

    monkeypatch.setattr("app.integrations.weather.open_meteo.httpx.AsyncClient", lambda **kwargs: ForecastClient(Response(payload)))
    item = connector(tmp_path)
    result = await item.fetch_forecast()
    assert result.mode == "live"
    assert item.forecast_cache_path.exists()
    params = captured["params"]
    assert isinstance(params, dict)
    assert "relative_humidity_2m" in str(params["current"])
    assert "precipitation_probability" in str(params["hourly"])
    assert params["latitude"] == 22.7196
    assert params["longitude"] == 75.8577
