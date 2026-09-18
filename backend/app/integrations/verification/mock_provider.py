from collections.abc import Sequence
from datetime import UTC, datetime

from app.domain.events import EventCategory, SystemAssessment
from app.domain.providers import (
    CandidateEvent,
    ClassificationResult,
    DuplicateResult,
    ProviderMetadata,
    VerificationContext,
    VerificationEventInput,
    VerificationProvider,
    VerificationResult,
)


class MockVerificationProvider(VerificationProvider):
    """Deliberately non-intelligent Phase 1 integration placeholder."""

    @staticmethod
    def _metadata() -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock-verification",
            provider_version="phase-1",
            generated_at=datetime.now(UTC),
        )

    async def classify(self, event: VerificationEventInput) -> ClassificationResult:
        return ClassificationResult(EventCategory.UNKNOWN, None, self._metadata())

    async def evaluate(
        self, event: VerificationEventInput, context: VerificationContext
    ) -> VerificationResult:
        return VerificationResult(
            assessment=SystemAssessment.UNAVAILABLE,
            score=None,
            reason_codes=("PROVIDER_NOT_IMPLEMENTED",),
            metadata=self._metadata(),
        )

    async def find_duplicates(
        self, event: VerificationEventInput, candidates: Sequence[CandidateEvent]
    ) -> list[DuplicateResult]:
        return []
