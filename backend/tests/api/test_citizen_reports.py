from app.api.dependencies import get_verification_provider
from app.models.event import RawIngestRecord, WeatherEvent
from fastapi.testclient import TestClient
from sqlalchemy import select


def report_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "description": "Heavy rainfall with waterlogging near the road.",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "observed_at": "2026-09-19T10:00:00Z",
        "state": "Maharashtra",
        "city": "Mumbai",
        "reporter_alias": "Demo resident",
    }
    payload.update(overrides)
    return payload


def test_citizen_report_uses_canonical_ingestion_and_provenance(client: TestClient) -> None:
    response = client.post("/api/v1/reports/citizen", json=report_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["source"]["name"] == "Citizen weather reports"
    assert body["source"]["source_type"] == "CITIZEN_REPORT"
    assert body["event_type"] == "UNKNOWN"
    assert body["severity"] == "UNSPECIFIED"
    assert body["admin_status"] == "UNREVIEWED"
    assert body["processing_status"] == "PARTIAL"
    assert body["metadata"]["origin_mode"] == "CITIZEN_REPORT"
    assert body["metadata"]["reporter_alias"] == "Demo resident"
    assert body["metadata"]["provider_status"]["verification"] == "UNAVAILABLE"
    assert body["external_id"].startswith("citizen:")
    with client.app.state.test_session_factory() as session:
        raw = session.scalar(select(RawIngestRecord))
        stored = session.scalar(select(WeatherEvent))
    assert raw is not None and raw.raw_payload["description"] == report_payload()["description"]
    assert raw.validation_status == "ACCEPTED"
    assert stored is not None and str(stored.id) == body["id"]


def test_citizen_report_accepts_safe_media_metadata(client: TestClient) -> None:
    response = client.post("/api/v1/reports/citizen", json=report_payload(media=[{"media_type": "IMAGE", "reference": "demo://media/citizen.jpg", "caption": "Controlled image reference"}]))
    assert response.status_code == 201
    assert response.json()["media_evidence"][0]["reference"] == "demo://media/citizen.jpg"
    assert response.json()["media_evidence"][0]["is_demo"] is False
    assert client.post("/api/v1/reports/citizen", json=report_payload(media=[{"media_type": "AUDIO", "reference": "demo://media/citizen.mp3"}])).status_code == 422
    assert client.post("/api/v1/reports/citizen", json=report_payload(media=[{"media_type": "IMAGE", "reference": "javascript:alert(1)"}])).status_code == 422
    assert client.post("/api/v1/reports/citizen", json=report_payload(media=[{"media_type": "IMAGE", "reference": "demo://media/1"}] * 4)).status_code == 422


def test_citizen_report_validates_required_fields_and_coordinates(client: TestClient) -> None:
    assert client.post("/api/v1/reports/citizen", json=report_payload(description=" ")).status_code == 422
    assert client.post("/api/v1/reports/citizen", json=report_payload(latitude=91)).status_code == 422
    assert client.post("/api/v1/reports/citizen", json=report_payload(longitude=181)).status_code == 422


def test_citizen_report_survives_provider_failure(client: TestClient) -> None:
    class FailingVerificationProvider:
        async def evaluate(self, *args: object) -> object:
            raise RuntimeError("provider unavailable")

    client.app.dependency_overrides[get_verification_provider] = FailingVerificationProvider
    response = client.post("/api/v1/reports/citizen", json=report_payload())
    assert response.status_code == 201
    assert response.json()["processing_status"] == "PARTIAL"
    assert response.json()["system_assessment"] == "UNAVAILABLE"
