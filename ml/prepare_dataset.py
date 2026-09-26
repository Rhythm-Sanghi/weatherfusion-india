"""Create reproducible source-aware train/validation/test manifests.

Only approved labelled records are accepted. This intentionally refuses the
synthetic pending examples shipped with the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def split_name(record: dict[str, object]) -> str:
    """Keep records from the same source dataset in the same split."""
    source_key = str(record["source_dataset"])
    bucket = int(hashlib.sha256(source_key.encode()).hexdigest()[:8], 16) % 100
    return "train" if bucket < 80 else "validation" if bucket < 90 else "test"


def prepare(input_path: Path, output_dir: Path) -> dict[str, int]:
    records = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line]
    approved = [record for record in records if record.get("annotation_status") == "APPROVED"]
    if not approved:
        raise ValueError("No APPROVED labels found; no training manifest was created.")
    output_dir.mkdir(parents=True, exist_ok=True)
    splits: dict[str, list[dict[str, object]]] = {"train": [], "validation": [], "test": []}
    for record in approved:
        splits[split_name(record)].append(record)
    for name, rows in splits.items():
        (output_dir / f"{name}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
        )
    return {name: len(rows) for name, rows in splits.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(prepare(arguments.input, arguments.output), sort_keys=True))
