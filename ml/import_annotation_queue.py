"""Validate lawful CSV/JSONL text exports and create a PENDING annotation queue."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REQUIRED = ("record_id", "report_text", "language", "source_dataset", "source_record_id", "source_type")


def read_rows(path: Path) -> list[dict[str, object]]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    raise ValueError("Input must be CSV or JSONL.")


def make_queue(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    queue: list[dict[str, object]] = []
    seen: set[str] = set()
    for position, row in enumerate(rows, 1):
        if any(not isinstance(row.get(field), str) or not str(row[field]).strip() for field in REQUIRED):
            raise ValueError(f"row {position}: missing required text/provenance field")
        record_id = str(row["record_id"])
        if record_id in seen: raise ValueError(f"row {position}: duplicate record_id {record_id}")
        seen.add(record_id)
        original_label = str(row.get("original_source_label") or "").strip()
        queue.append({
            "record_id": record_id, "report_text": str(row["report_text"]).strip(), "language": str(row["language"]).strip(),
            "source_dataset": str(row["source_dataset"]).strip(), "source_record_id": str(row["source_record_id"]).strip(), "source_type": str(row["source_type"]).strip(),
            "source_reference": str(row.get("source_reference") or "").strip() or None,
            "observation_time": str(row.get("observation_time") or "").strip() or None, "received_time": str(row.get("received_time") or "").strip() or None,
            "weather_relevance_label": None, "primary_event_type_label": None, "annotation_status": "PENDING_REVIEW", "annotator_id": None,
            "annotation_guideline_version": "v1", "incident_group_id": row.get("incident_group_id") or None, "duplicate_group_id": row.get("duplicate_group_id") or None,
            "notes": f"Original source label (unreviewed): {original_label}" if original_label else None, "synthetic_fixture": False,
        })
    return queue


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("input", type=Path); parser.add_argument("output", type=Path); args = parser.parse_args()
    rows = make_queue(read_rows(args.input)); args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"queued": len(rows)}, sort_keys=True))
