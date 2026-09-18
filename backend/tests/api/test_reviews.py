from typing import Any

from fastapi.testclient import TestClient
from .test_events import event_payload


def create_event(client: TestClient, **overrides: Any) -> dict[str, Any]:
    response = client.post("/api/v1/events", json=event_payload(**overrides))
    assert response.status_code == 201
    return response.json()


def review_payload(version: int, action: str = "VERIFY", **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"action": action, "reviewer_id": "demo-reviewer-01", "reviewer_name": "SIH Demo Operator", "reason": "Evidence reviewed", "expected_version": version}
    payload.update(overrides)
    return payload


def test_review_queue_orders_unreviewed_events(client: TestClient) -> None:
    low = create_event(client, severity="LOW")
    critical = create_event(client, external_id="citizen-002", severity="CRITICAL")
    queue = client.get("/api/v1/review-queue")
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()] == [critical["id"], low["id"]]


def test_actions_create_decision_audit_and_increment_version(client: TestClient) -> None:
    for index, action in enumerate(["VERIFY", "REJECT", "ESCALATE"]):
        event = create_event(client, external_id=f"review-{index}")
        result = client.post(f"/api/v1/events/{event['id']}/reviews", json=review_payload(event["version"], action))
        assert result.status_code == 200
        assert result.json()["new_admin_status"] == {"VERIFY": "VERIFIED", "REJECT": "REJECTED", "ESCALATE": "ESCALATED"}[action]
        assert result.json()["event_version"] == event["version"] + 1
        updated = client.get(f"/api/v1/events/{event['id']}").json()
        assert updated["admin_status"] == result.json()["new_admin_status"]
        audit = client.get(f"/api/v1/events/{event['id']}/audit").json()
        assert len(audit) == 1 and audit[0]["action"] == action


def test_review_validation_and_conflict_are_safe(client: TestClient) -> None:
    event = create_event(client)
    assert client.post(f"/api/v1/events/{event['id']}/reviews", json=review_payload(event["version"], reason=" ")).status_code == 422
    conflict = client.post(f"/api/v1/events/{event['id']}/reviews", json=review_payload(event["version"] + 1))
    assert conflict.status_code == 409
    assert client.get(f"/api/v1/events/{event['id']}").json()["admin_status"] == "UNREVIEWED"
    assert client.get(f"/api/v1/events/{event['id']}/audit").json() == []
    success = client.post(f"/api/v1/events/{event['id']}/reviews", json=review_payload(event["version"]))
    assert success.status_code == 200
    assert client.post(f"/api/v1/events/{event['id']}/reviews", json=review_payload(event["version"] + 1)).status_code == 400
    assert client.post("/api/v1/events/00000000-0000-0000-0000-000000000000/reviews", json=review_payload(1)).status_code == 404
