import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.domain.events import EventCategory
from app.domain.providers import VerificationEventInput
from app.integrations.verification.ml_provider import MLVerificationProvider


def _artifact() -> dict[str, object]:
    return {
        "format": "weatherfusion-naive-bayes-v1", "model_version": "test-v1", "dataset_sha256": "abc",
        "relevance": {"counts": {"WEATHER_RELEVANT": 2, "NOT_WEATHER_RELEVANT": 1}, "words": {"WEATHER_RELEVANT": {"flood": 3, "rain": 2}, "NOT_WEATHER_RELEVANT": {"concert": 2}}, "totals": {"WEATHER_RELEVANT": 5, "NOT_WEATHER_RELEVANT": 2}, "vocabulary": ["flood", "rain", "concert"]},
        "event_type": {"counts": {"FLOOD": 2}, "words": {"FLOOD": {"flood": 3, "rain": 2}}, "totals": {"FLOOD": 5}, "vocabulary": ["flood", "rain"]},
    }


@pytest.mark.asyncio
async def test_ml_provider_returns_versioned_event_type_evidence(tmp_path) -> None:
    path = tmp_path / "model.json"
    path.write_text(json.dumps(_artifact()), encoding="utf-8")
    provider = MLVerificationProvider(None, Settings(verification_model_artifact_path=path))  # type: ignore[arg-type]
    result = await provider.classify(VerificationEventInput(uuid4(), "flood rain", EventCategory.UNKNOWN, datetime.now(UTC)))
    assert result.event_type is EventCategory.FLOOD
    assert result.confidence is None
    assert result.details is not None and result.details["dataset_sha256"] == "abc"


def test_ml_provider_rejects_missing_artifact() -> None:
    with pytest.raises(Exception, match="VERIFICATION_MODEL_ARTIFACT_PATH"):
        MLVerificationProvider(None, Settings())  # type: ignore[arg-type]
