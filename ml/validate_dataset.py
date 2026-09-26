"""Validate annotation-ready JSONL data without treating it as training data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EVENT_TYPES = {
    "HEAVY_RAINFALL", "FLOOD", "THUNDERSTORM", "HEATWAVE",
    "FOG", "DUST_STORM", "STRONG_WIND", "UNKNOWN",
}


def validate(path: Path, *, approved_only: bool = False) -> dict[str, int]:
    seen: set[str] = set()
    counts = {"records": 0, "approved": 0, "pending": 0}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        row = json.loads(line)
        record_id = row.get("record_id")
        if not isinstance(record_id, str) or not record_id or record_id in seen:
            raise ValueError(f"line {line_number}: record_id must be unique and nonempty")
        seen.add(record_id)
        relevance = row.get("weather_relevance_label")
        event_type = row.get("primary_event_type_label")
        if relevance in {"NOT_WEATHER_RELEVANT", "UNCERTAIN"} and event_type is not None:
            raise ValueError(f"line {line_number}: non-trainable relevance requires null event type")
        if event_type is not None and event_type not in EVENT_TYPES:
            raise ValueError(f"line {line_number}: unsupported event type")
        approved = row.get("annotation_status") == "APPROVED"
        if approved and not row.get("annotator_id"):
            raise ValueError(f"line {line_number}: approved annotation requires annotator_id")
        if approved_only and (not approved or row.get("synthetic_fixture")):
            raise ValueError(f"line {line_number}: not eligible for approved corpus")
        counts["records"] += 1
        counts["approved" if approved else "pending"] += 1
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--approved-only", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(validate(arguments.dataset, approved_only=arguments.approved_only), sort_keys=True))
