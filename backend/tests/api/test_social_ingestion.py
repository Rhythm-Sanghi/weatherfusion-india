from app.models.event import MediaEvidence, RawIngestRecord, WeatherEvent
from fastapi.testclient import TestClient
from sqlalchemy import func, select


def test_controlled_social_ingestion_preserves_raw_media_and_is_idempotent(client: TestClient) -> None:
    first = client.post("/api/v1/ingestion/social")
    assert first.status_code == 200
    assert first.json() == {"source": "controlled_social_feed", "received": 20, "matched": 18, "created": 18, "duplicates": 0, "failed": 0, "mode": "controlled"}
    second = client.post("/api/v1/ingestion/social")
    assert second.status_code == 200
    assert second.json()["created"] == 0
    assert second.json()["duplicates"] == 18
    with client.app.state.test_session_factory() as session:
        assert session.scalar(select(func.count()).select_from(WeatherEvent)) == 18
        assert session.scalar(select(func.count()).select_from(RawIngestRecord)) == 18
        media = session.scalar(select(MediaEvidence).where(MediaEvidence.reference == "demo://media/social-001.jpg"))
    assert media is not None and media.media_type == "IMAGE"


def test_controlled_demo_feed_and_scenarios_are_explicitly_labelled(client: TestClient) -> None:
    feed = client.get("/api/v1/demo/feed")
    assert feed.status_code == 200
    assert feed.json()["mode"] == "controlled_demo"
    assert len(feed.json()["items"]) == 18
    scenarios = client.get("/api/v1/demo/scenarios")
    assert scenarios.status_code == 200
    assert {scenario["id"] for scenario in scenarios.json()} == {
        "mumbai-flood", "guwahati-storm", "rajasthan-dust"
    }
    activated = client.post("/api/v1/demo/scenarios/mumbai-flood")
    assert activated.status_code == 200
    assert activated.json()["status"] == "activated"
    assert activated.json()["created"] == 2
