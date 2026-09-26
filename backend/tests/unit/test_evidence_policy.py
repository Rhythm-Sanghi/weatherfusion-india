from app.services.evidence_policy import EvidenceComponent, summarize


def test_evidence_score_uses_only_available_weight_and_reports_coverage() -> None:
    result = summarize(
        (
            EvidenceComponent("source_reliability", 0.25, True, 0.8, ("SOURCE_RELIABILITY_PROFILE",)),
            EvidenceComponent("independent_corroboration", 0.25, True, 0.4, ("ONE_INDEPENDENT_SOURCE",), ("event-1",)),
            EvidenceComponent("validated_ml_evidence", 0.15, False, None, ("VALIDATED_ML_EVIDENCE_NOT_AVAILABLE",)),
        ),
        method_version="evidence-ranking-v1",
    )
    assert result["score"] == 0.6
    assert result["coverage"] == 0.5
    assert result["components"][2]["contribution"] is None
    assert result["evidence_references"] == ["event-1"]


def test_evidence_score_is_unavailable_without_any_available_channel() -> None:
    result = summarize(
        (EvidenceComponent("validated_ml_evidence", 0.15, False, None, ("NOT_AVAILABLE",)),),
        method_version="evidence-ranking-v1",
    )
    assert result["score"] is None
    assert result["coverage"] == 0
