"""Prepare auditable NOAA Storm Events artifacts without altering source files.

This script intentionally refuses to create train/validation/test datasets unless
the source contains both suitable text and an episode-aware grouping identifier.
It is designed for the WeatherFusion report-text classifier, not to manufacture
labels from incomplete historical records.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = {
    "EPISODE_ID", "EVENT_ID", "EVENT_TYPE", "BEGIN_DATE_TIME", "END_DATE_TIME",
    "STATE", "CZ_NAME", "BEGIN_LOCATION", "END_LOCATION", "BEGIN_LAT", "BEGIN_LON",
    "END_LAT", "END_LON", "EPISODE_NARRATIVE", "EVENT_NARRATIVE", "DATA_SOURCE",
}
TIMESTAMP_FORMAT = "%d-%b-%y %H:%M:%S"
EVENT_TYPE_SPACE = re.compile(r"\s+")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text(value: str | None) -> str:
    return (value or "").strip()


def normalise_event_type(value: str | None) -> str:
    return EVENT_TYPE_SPACE.sub(" ", text(value)).upper()


def parse_timestamp(value: str | None) -> datetime | None:
    candidate = text(value)
    if not candidate:
        return None
    try:
        return datetime.strptime(candidate, TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None


def valid_coordinate(value: str | None, minimum: float, maximum: float) -> bool:
    try:
        coordinate = float(text(value))
    except ValueError:
        return False
    return math.isfinite(coordinate) and minimum <= coordinate <= maximum


def record_issue_flags(row: dict[str, str]) -> dict[str, bool]:
    begin_lat_ok = valid_coordinate(row.get("BEGIN_LAT"), -90, 90)
    begin_lon_ok = valid_coordinate(row.get("BEGIN_LON"), -180, 180)
    end_lat_ok = valid_coordinate(row.get("END_LAT"), -90, 90)
    end_lon_ok = valid_coordinate(row.get("END_LON"), -180, 180)
    return {
        "missing_event_narrative": not bool(text(row.get("EVENT_NARRATIVE"))),
        "missing_episode_narrative": not bool(text(row.get("EPISODE_NARRATIVE"))),
        "missing_episode_id": not bool(text(row.get("EPISODE_ID"))),
        "missing_begin_timestamp": parse_timestamp(row.get("BEGIN_DATE_TIME")) is None,
        "missing_end_timestamp": parse_timestamp(row.get("END_DATE_TIME")) is None,
        "invalid_begin_coordinates": not (begin_lat_ok and begin_lon_ok),
        "invalid_end_coordinates": not (end_lat_ok and end_lon_ok),
        "missing_event_type": not bool(normalise_event_type(row.get("EVENT_TYPE"))),
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def open_source_csv(path: Path):
    """Open either the original NOAA gzip download or an extracted CSV read-only."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("r", encoding="utf-8-sig", newline="")


def split_for_episode(episode_id: str) -> str:
    """Deterministically keep every event in an episode in one partition."""
    bucket = int(hashlib.sha256(episode_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    return "train" if bucket < 80 else "validation" if bucket < 90 else "test"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--download-date",
        default=None,
        help="ISO-8601 date supplied by the downloader. Omit when unknown rather than guessing.",
    )
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    files = sorted([*source_dir.glob("StormEvents_details-ftp_v*.csv"), *source_dir.glob("StormEvents_details-ftp_v*.csv.gz")])
    if not files:
        raise SystemExit(f"No NOAA Storm Events detail CSV files found in {source_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    source_files: list[dict[str, Any]] = []
    expected_headers: list[str] | None = None
    for file_path in files:
        with open_source_csv(file_path) as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            missing = sorted(REQUIRED_COLUMNS.difference(headers))
            if missing:
                raise SystemExit(f"{file_path.name} is missing required columns: {', '.join(missing)}")
            if expected_headers is None:
                expected_headers = headers
            elif headers != expected_headers:
                raise SystemExit(f"{file_path.name} has a different column order/schema from earlier source files")
            count = 0
            for line_number, row in enumerate(reader, start=2):
                rows.append({**row, "_source_file": file_path.name, "_source_line": str(line_number)})
                count += 1
        source_files.append(
            {
                "filename": file_path.name,
                "sha256": sha256(file_path),
                "bytes": file_path.stat().st_size,
                "last_modified_utc": datetime.fromtimestamp(file_path.stat().st_mtime, UTC).isoformat(),
                "record_count": count,
            }
        )

    assert expected_headers is not None
    source_id_counts = Counter(text(row.get("EVENT_ID")) for row in rows if text(row.get("EVENT_ID")))
    raw_event_type_counts = Counter(text(row.get("EVENT_TYPE")) for row in rows)
    normalized_event_type_counts = Counter(normalise_event_type(row.get("EVENT_TYPE")) for row in rows)
    normalized_to_raw: dict[str, set[str]] = {}
    for raw in raw_event_type_counts:
        normalized_to_raw.setdefault(normalise_event_type(raw), set()).add(raw)

    audits: list[dict[str, Any]] = []
    structured_candidates: list[dict[str, str]] = []
    text_candidates: list[dict[str, str]] = []
    for row in rows:
        flags = record_issue_flags(row)
        begin_timestamp = parse_timestamp(row.get("BEGIN_DATE_TIME"))
        candidate = (
            not flags["missing_event_type"]
            and not flags["missing_begin_timestamp"]
            and not flags["invalid_begin_coordinates"]
            and bool(text(row.get("EVENT_ID")))
        )
        audit_row = {
            "source_file": row["_source_file"],
            "source_line": row["_source_line"],
            "event_id": text(row.get("EVENT_ID")),
            "episode_id": text(row.get("EPISODE_ID")),
            "event_type_original": text(row.get("EVENT_TYPE")),
            "event_type_normalized": normalise_event_type(row.get("EVENT_TYPE")),
            **flags,
            "structured_event_type_candidate": candidate,
            "text_event_type_candidate": (
                not flags["missing_event_type"]
                and not flags["missing_begin_timestamp"]
                and bool(text(row.get("EVENT_ID")))
                and not flags["missing_event_narrative"]
            ),
            "episode_aware_split_eligible": (
                not flags["missing_event_type"]
                and not flags["missing_begin_timestamp"]
                and bool(text(row.get("EVENT_ID")))
                and not flags["missing_event_narrative"]
                and not flags["missing_episode_id"]
            ),
        }
        audits.append(audit_row)
        if candidate:
            structured_candidates.append(
                {
                    **{header: row.get(header, "") for header in expected_headers},
                    "SOURCE_FILE": row["_source_file"],
                    "SOURCE_LINE": row["_source_line"],
                    "BEGIN_TIMESTAMP_UTC": begin_timestamp.isoformat() if begin_timestamp else "",
                    "EVENT_TYPE_NORMALIZED": normalise_event_type(row.get("EVENT_TYPE")),
                    "DATASET_ROLE": "STRUCTURED_EVENT_TYPE_CANDIDATE_ONLY",
                    "TEXT_CLASSIFICATION_ELIGIBLE": "false",
                    "EPISODE_AWARE_SPLIT_ELIGIBLE": "false",
                }
            )
        if audit_row["episode_aware_split_eligible"]:
            text_candidates.append(
                {
                    **{header: row.get(header, "") for header in expected_headers},
                    "SOURCE_FILE": row["_source_file"],
                    "SOURCE_LINE": row["_source_line"],
                    "BEGIN_TIMESTAMP_UTC": begin_timestamp.isoformat() if begin_timestamp else "",
                    "EVENT_TYPE_NORMALIZED": normalise_event_type(row.get("EVENT_TYPE")),
                    "EPISODE_GROUP_ID": text(row.get("EPISODE_ID")),
                    "DATASET_ROLE": "NOAA_EVENT_TYPE_TEXT_CLASSIFICATION",
                }
            )

    audit_counts = Counter()
    for record in audits:
        for key, value in record.items():
            if isinstance(value, bool) and value:
                audit_counts[key] += 1

    duplicate_ids = sorted(event_id for event_id, count in source_id_counts.items() if count > 1)
    event_type_inconsistencies = {
        normalized: sorted(raw_values)
        for normalized, raw_values in normalized_to_raw.items()
        if len(raw_values) > 1
    }
    structured_distribution = Counter(row["EVENT_TYPE_NORMALIZED"] for row in structured_candidates)
    text_eligible = len(text_candidates)
    episode_split_eligible = len(text_candidates)
    splits: dict[str, list[dict[str, str]]] = {"train": [], "validation": [], "test": []}
    for candidate in text_candidates:
        splits[split_for_episode(candidate["EPISODE_GROUP_ID"])].append(candidate)
    split_distributions = {
        split_name: dict(sorted(Counter(row["EVENT_TYPE_NORMALIZED"] for row in split_rows).items()))
        for split_name, split_rows in splits.items()
    }
    split_episode_counts = {
        split_name: len({row["EPISODE_GROUP_ID"] for row in split_rows})
        for split_name, split_rows in splits.items()
    }
    usable_splits = all(splits.values()) and len({row["EVENT_TYPE_NORMALIZED"] for row in text_candidates}) >= 2

    manifest = {
        "dataset_name": "NOAA Storm Events Database detail files",
        "source": "NOAA National Centers for Environmental Information Storm Events Database",
        "source_url": "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/",
        "dataset_version": "ftp_v1.0 as encoded in source filenames",
        "source_directory": str(source_dir),
        "download_date": args.download_date or "UNKNOWN_NOT_EMBEDDED_IN_FILES",
        "download_date_note": "The source files do not provide a verified download date. The cYYYYMMDD filename suffix is retained as a file revision/date token and is not treated as the download date.",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_files": source_files,
        "original_record_count": len(rows),
        "source_schema": expected_headers,
    }
    adequacy = {
        "event_type_descriptive_analysis": {
            "adequate": True,
            "reason": "EVENT_TYPE is present and retained as the NOAA-recorded source label.",
            "ground_truth": "NOAA-recorded EVENT_TYPE",
        },
        "structured_metadata_event_type_classification": {
            "adequate": False,
            "reason": "Rows have event-type labels and mostly valid start coordinates/timestamps, but all EPISODE_ID values are blank. An incident-aware or episode-aware split cannot be created from this source alone.",
            "eligible_rows_before_split_requirement": len(structured_candidates),
            "class_distribution": dict(sorted(structured_distribution.items())),
        },
        "weather_report_text_event_type_classification": {
            "adequate": usable_splits,
            "reason": (
                "EVENT_NARRATIVE, NOAA EVENT_TYPE ground-truth labels, and EPISODE_ID are available; "
                "records are split deterministically by EPISODE_ID. EPISODE_ID prevents leakage only and is not a duplicate-report label."
                if usable_splits else
                "Suitable narrative-bearing records with at least two classes in non-empty episode-aware partitions are unavailable."
            ),
            "eligible_rows": text_eligible,
            "class_distribution": dict(sorted(Counter(row["EVENT_TYPE_NORMALIZED"] for row in text_candidates).items())),
        },
        "false_report_or_truthfulness_classification": {
            "adequate": False,
            "reason": "NOAA event records do not include false-report, truthfulness, or human-verification labels.",
        },
        "verified_duplicate_report_classification": {
            "adequate": False,
            "reason": "No duplicate-report ground-truth labels are present. EPISODE_ID is blank in every supplied row and, even when present in other NOAA data, is not a verified duplicate-report label.",
        },
        "precision_recall_f1": {
            "adequate": usable_splits,
            "reason": (
                "The NOAA EVENT_TYPE task has ground-truth labels and a held-out episode-aware test partition. "
                "Metrics may be calculated only for that task."
                if usable_splits else
                "No supported predictive task in this source can meet the required episode-aware held-out split. Metrics are intentionally not calculated."
            ),
        },
    }
    report = {
        "manifest": manifest,
        "audit": {
            "missing_event_narrative": audit_counts["missing_event_narrative"],
            "missing_episode_narrative": audit_counts["missing_episode_narrative"],
            "missing_begin_timestamp_or_invalid_format": audit_counts["missing_begin_timestamp"],
            "missing_end_timestamp_or_invalid_format": audit_counts["missing_end_timestamp"],
            "invalid_begin_coordinate_pair": audit_counts["invalid_begin_coordinates"],
            "invalid_end_coordinate_pair": audit_counts["invalid_end_coordinates"],
            "missing_event_type": audit_counts["missing_event_type"],
            "missing_episode_id": audit_counts["missing_episode_id"],
            "duplicate_source_event_ids": len(duplicate_ids),
            "duplicate_source_event_id_records_beyond_first": sum(source_id_counts[item] - 1 for item in duplicate_ids),
            "event_type_normalization_inconsistencies": event_type_inconsistencies,
        },
        "structured_candidate_dataset": {
            "records": len(structured_candidates),
            "excluded": len(rows) - len(structured_candidates),
            "class_distribution": dict(sorted(structured_distribution.items())),
            "limitation": "This registry requires valid start coordinates for spatial analysis. Text classification uses a separate narrative/label/timestamp/episode eligibility rule and retains coordinate audit flags rather than discarding text solely for missing coordinates.",
        },
        "text_classification_dataset": {
            "eligible_records": text_eligible,
            "excluded_records": len(rows) - text_eligible,
            "class_distribution": dict(sorted(Counter(row["EVENT_TYPE_NORMALIZED"] for row in text_candidates).items())),
            "status": "CREATED" if usable_splits else "NOT_CREATED_INSUFFICIENT_GROUPED_TEXT",
        },
        "splits": {
            "train": len(splits["train"]) if usable_splits else 0,
            "validation": len(splits["validation"]) if usable_splits else 0,
            "test": len(splits["test"]) if usable_splits else 0,
            "episode_group_counts": split_episode_counts if usable_splits else {},
            "class_distribution": split_distributions if usable_splits else {},
            "status": "CREATED_EPISODE_AWARE" if usable_splits else "NOT_CREATED_INSUFFICIENT_GROUPED_TEXT",
        },
        "task_adequacy": adequacy,
    }

    write_json(output_dir / "source_manifest.json", manifest)
    write_json(output_dir / "audit_report.json", report)
    write_json(output_dir / "task_adequacy.json", adequacy)
    with (output_dir / "record_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audits[0]))
        writer.writeheader()
        writer.writerows(audits)
    candidate_columns = [*expected_headers, "SOURCE_FILE", "SOURCE_LINE", "BEGIN_TIMESTAMP_UTC", "EVENT_TYPE_NORMALIZED", "DATASET_ROLE", "TEXT_CLASSIFICATION_ELIGIBLE", "EPISODE_AWARE_SPLIT_ELIGIBLE"]
    with (output_dir / "structured_event_type_candidates_not_for_text_ml.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=candidate_columns)
        writer.writeheader()
        writer.writerows(structured_candidates)
    text_columns = [*expected_headers, "SOURCE_FILE", "SOURCE_LINE", "BEGIN_TIMESTAMP_UTC", "EVENT_TYPE_NORMALIZED", "EPISODE_GROUP_ID", "DATASET_ROLE"]
    with (output_dir / "event_type_text_candidates.jsonl").open("w", encoding="utf-8") as handle:
        for row in text_candidates:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    if usable_splits:
        for split_name, split_rows in splits.items():
            with (output_dir / f"{split_name}.jsonl").open("w", encoding="utf-8") as handle:
                for row in split_rows:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")

    print(json.dumps({
        "original_records": len(rows),
        "structured_candidates": len(structured_candidates),
        "text_ml_eligible": text_eligible,
        "episode_aware_split_eligible": episode_split_eligible,
        "split_counts": {name: len(rows) for name, rows in splits.items()} if usable_splits else {},
        "output_dir": str(output_dir),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
