"""Explainable prototype evidence policy; this is not an incident-truth model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceComponent:
    name: str
    weight: float
    available: bool
    value: float | None
    reason_codes: tuple[str, ...]
    evidence_references: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        contribution = self.weight * self.value if self.available and self.value is not None else None
        return {
            "name": self.name,
            "weight": self.weight,
            "available": self.available,
            "value": self.value,
            "contribution": contribution,
            "reason_codes": list(self.reason_codes),
            "evidence_references": list(self.evidence_references),
        }


def summarize(components: tuple[EvidenceComponent, ...], *, method_version: str) -> dict[str, object]:
    available_weight = sum(item.weight for item in components if item.available)
    weighted_support = sum(
        item.weight * item.value
        for item in components
        if item.available and item.value is not None
    )
    score = weighted_support / available_weight if available_weight else None
    return {
        "method_version": method_version,
        "score": round(score, 6) if score is not None else None,
        "coverage": round(available_weight, 6),
        "components": [item.as_dict() for item in components],
        "reason_codes": [code for item in components for code in item.reason_codes],
        "evidence_references": [reference for item in components for reference in item.evidence_references],
        "interpretation": "Prototype evidence ranking only. It does not establish incident truth and does not replace human review.",
    }
