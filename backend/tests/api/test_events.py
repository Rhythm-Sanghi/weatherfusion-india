from typing import Any

from app.api.dependencies import get_geospatial_provider, get_verification_provider
from fastapi.testclient import TestClient


def event_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": "Citizen weather desk",
        "source_type": "CITIZEN",
        "external_id": "citizen-001",
        "event_type": "HEAVY_RAINFALL",
        "severity": "HIGH",
        "description": "Heavy rain near the station.",
        "latitude": 19.076,
        "longitude": 72.8777,
        "state": "Maharashtra",
        "city": "Mumbai",
        "observed_at": "2026-09-18T10:00:00Z",
        "metadata": {"demo": True},
    }
    payload.update(overrides)
    return payload


def test_create_persists_and_retrieves_event(client: TestClient) -> None:
    created = client.post("/api/v1/events", json=event_payload())

    assert created.status_code == 201
    body = created.json()
    assert body["processing_status"] == "PARTIAL"
    assert body["system_assessment"] == "UNAVAILABLE"
    assert body["source"]["name"] == "Citizen weather desk"
    assert body["metadata"]["provider_status"]["verification"] == "UNAVAILABLE"

    retrieved = client.get(f"/api/v1/events/{body['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json()["id"] == body["id"]


def test_event_request_validation(client: TestClient) -> None:
    assert client.post("/api/v1/events", json=event_payload(latitude=91)).status_code == 422
    assert client.post("/api/v1/events", json=event_payload(longitude=181)).status_code == 422
    assert client.post("/api/v1/events", json=event_payload(latitude=None)).status_code == 422
    assert client.post("/api/v1/events", json=event_payload(longitude=None)).status_code == 422
    assert (
        client.post("/api/v1/events", json=event_payload(event_type="RAINBOW")).status_code == 422
    )
    assert client.post("/api/v1/events", json={"source": "Citizen"}).status_code == 422


def test_duplicate_source_external_id_returns_conflict(client: TestClient) -> None:
    assert client.post("/api/v1/events", json=event_payload()).status_code == 201
    assert client.post("/api/v1/events", json=event_payload()).status_code == 409


def test_list_filters_pagination_and_detail_not_found(client: TestClient) -> None:
    assert client.post("/api/v1/events", json=event_payload()).status_code == 201
    assert (
        client.post(
            "/api/v1/events",
            json=event_payload(
                external_id="citizen-002",
                event_type="FLOOD",
                state="Kerala",
                observed_at="2026-09-18T11:00:00Z",
            ),
        ).status_code
        == 201
    )

    by_type = client.get("/api/v1/events?event_type=FLOOD")
    assert by_type.json()["total"] == 1
    assert by_type.json()["items"][0]["state"] == "Kerala"
    assert client.get("/api/v1/events?state=Maharashtra&page_size=1").json()["total"] == 1
    assert client.get("/api/v1/events?page=3&page_size=1").json()["items"] == []
    assert client.get("/api/v1/events/00000000-0000-0000-0000-000000000000").status_code == 404


def test_summary_counts_events(client: TestClient) -> None:
    assert client.post("/api/v1/events", json=event_payload()).status_code == 201
    assert (
        client.post("/api/v1/events", json=event_payload(external_id="citizen-002")).status_code
        == 201
    )

    summary = client.get("/api/v1/events/summary")
    assert summary.status_code == 200
    assert summary.json()["total_events"] == 2
    assert summary.json()["by_processing_status"] == {"PARTIAL": 2}


def test_provider_failure_does_not_rollback_event(client: TestClient) -> None:
    class FailingVerificationProvider:
        async def evaluate(self, *args: object) -> object:
            raise RuntimeError("provider unavailable")

    client.app.dependency_overrides[get_verification_provider] = FailingVerificationProvider
    response = client.post("/api/v1/events", json=event_payload())

    assert response.status_code == 201
    assert response.json()["processing_status"] == "PARTIAL"
    assert response.json()["system_assessment"] == "UNAVAILABLE"
    assert response.json()["metadata"]["provider_status"]["verification"] == "UNAVAILABLE"


def test_geospatial_failure_does_not_rollback_event(client: TestClient) -> None:
    class FailingGeospatialProvider:
        async def enrich_location(self, *args: object) -> object:
            raise RuntimeError("PostGIS unavailable")

    client.app.dependency_overrides[get_geospatial_provider] = FailingGeospatialProvider
    response = client.post("/api/v1/events", json=event_payload())

    assert response.status_code == 201
    assert response.json()["processing_status"] == "PARTIAL"
    assert response.json()["metadata"]["provider_status"]["geospatial"] == "UNAVAILABLE"


def test_spatial_routes_validate_radius_and_preserve_mock_behavior(client: TestClient) -> None:
    created = client.post("/api/v1/events", json=event_payload()).json()

    assert client.get("/api/v1/events/00000000-0000-0000-0000-000000000000/nearby").status_code == 404
    assert client.get(f"/api/v1/events/{created['id']}/nearby?radius_meters=0").status_code == 422
    nearby = client.get(f"/api/v1/events/{created['id']}/nearby")
    assert nearby.status_code == 200
    assert nearby.json()["provider"]["name"] == "mock"
    assert nearby.json()["items"] == []

    geojson = client.get("/api/v1/events/map/events")
    assert geojson.status_code == 200
    assert geojson.json() == {"type": "FeatureCollection", "features": []}
