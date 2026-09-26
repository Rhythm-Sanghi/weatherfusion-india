"""Artifact-backed, local classification provider.

The artifact is intentionally a JSON file so it can be inspected and versioned.
It is not loaded unless ``VERIFICATION_PROVIDER=ml`` is selected.
"""
from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ProviderConfigurationError
from app.domain.events import EventCategory
from app.domain.providers import ClassificationResult, ProviderMetadata, VerificationEventInput
from app.integrations.verification.operational_provider import OperationalVerificationProvider

TOKEN = re.compile(r"[\w']+", re.UNICODE)


class MLVerificationProvider(OperationalVerificationProvider):
    """Use the operational evidence policy plus a versioned text artifact."""

    def __init__(self, session: Session, settings: Settings) -> None:
        super().__init__(session, settings)
        path = settings.verification_model_artifact_path
        if path is None:
            raise ProviderConfigurationError(
                "VERIFICATION_PROVIDER=ml requires VERIFICATION_MODEL_ARTIFACT_PATH."
            )
        self.path = Path(path)
        try:
            self.artifact = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ProviderConfigurationError(f"Cannot load verification model artifact: {self.path}") from exc
        if self.artifact.get("format") != "weatherfusion-naive-bayes-v1":
            raise ProviderConfigurationError("Unsupported verification model artifact format.")
        if not isinstance(self.artifact.get("relevance"), dict):
            raise ProviderConfigurationError("Verification model artifact has no relevance model.")

    def _metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="artifact-ml-verification",
            provider_version=str(self.artifact.get("model_version", "naive-bayes-v1")),
            generated_at=datetime.now(UTC),
        )

    @staticmethod
    def _scores(model: dict[str, object], text: str) -> list[tuple[str, float]]:
        counts = model.get("counts") or {}
        words = model.get("words") or {}
        totals = model.get("totals") or {}
        vocabulary = model.get("vocabulary") or []
        if not all(isinstance(value, dict) for value in (counts, words, totals)) or not isinstance(vocabulary, list):
            raise ProviderConfigurationError("Verification model artifact has invalid model data.")
        total_documents = sum(int(value) for value in counts.values())
        if total_documents <= 0:
            raise ProviderConfigurationError("Verification model artifact has no training documents.")
        size = max(1, len(vocabulary))
        output: list[tuple[str, float]] = []
        for label, count in counts.items():
            bag = words.get(label, {})
            score = math.log(int(count) / total_documents)
            for token in TOKEN.findall(text.casefold()):
                score += math.log((int(bag.get(token, 0)) + 1) / (int(totals.get(label, 0)) + size))
            output.append((str(label), score))
        return sorted(output, key=lambda item: (-item[1], item[0]))

    async def classify(self, event: VerificationEventInput) -> ClassificationResult:
        relevance = self._scores(self.artifact["relevance"], event.text)
        label, score = relevance[0]
        margin = score - relevance[1][1] if len(relevance) > 1 else score
        details: dict[str, object] = {
            "model_version": self._metadata().provider_version,
            "dataset_sha256": self.artifact.get("dataset_sha256"),
            "prediction_label": label,
            "decision_margin": round(margin, 6),
            "threshold": self.settings.verification_ml_minimum_margin,
        }
        if label != "WEATHER_RELEVANT" or margin < self.settings.verification_ml_minimum_margin:
            return ClassificationResult(EventCategory.UNKNOWN, None, self._metadata(), details)
        event_model = self.artifact.get("event_type")
        if not isinstance(event_model, dict):
            details["reason_code"] = "EVENT_TYPE_MODEL_NOT_INSTALLED"
            return ClassificationResult(EventCategory.UNKNOWN, None, self._metadata(), details)
        event_label, event_score = self._scores(event_model, event.text)[0]
        try:
            category = EventCategory(event_label)
        except ValueError:
            details["reason_code"] = "ARTIFACT_RETURNED_UNSUPPORTED_EVENT_TYPE"
            return ClassificationResult(EventCategory.UNKNOWN, None, self._metadata(), details)
        details["event_type_decision_score"] = round(event_score, 6)
        # A margin is intentionally exposed as a decision signal, not confidence.
        return ClassificationResult(category, None, self._metadata(), details)
