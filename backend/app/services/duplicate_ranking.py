"""Deterministic candidate ranking; candidates are never duplicate decisions."""
from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher

from app.domain.providers import (
    CandidateEvent,
    DuplicateResult,
    ProviderMetadata,
    VerificationEventInput,
)


def rank_duplicate_candidates(event: VerificationEventInput, candidates: list[CandidateEvent], metadata: ProviderMetadata) -> list[DuplicateResult]:
    """Rank supplied bounded candidates by text and time only; no records are mutated."""
    if not event.text.strip():
        return []
    ranked: list[tuple[float, CandidateEvent]] = []
    for candidate in candidates:
        if not candidate.text.strip():
            continue
        text_score = SequenceMatcher(None, event.text.casefold(), candidate.text.casefold()).ratio()
        time_score = _time_score(event.observed_at, candidate.observed_at)
        score = round(0.8 * text_score + 0.2 * time_score, 6)
        ranked.append((score, candidate))
    return [DuplicateResult(candidate.event_id, score, metadata) for score, candidate in sorted(ranked, key=lambda item: (-item[0], str(item[1].event_id)))]


def _time_score(left: datetime, right: datetime | None) -> float:
    if right is None:
        return 0.0
    return max(0.0, 1.0 - abs((left - right).total_seconds()) / 86_400)
