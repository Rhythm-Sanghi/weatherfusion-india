"""Inspect pinned CREXWET releases without hydrating or redistributing tweets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE_URL = "https://zenodo.org/records/17950332"
LICENSE = "CC BY 4.0"
VERSION = "CREXWET v1 (2025-12-16)"


def inspect_dataset(directory: Path) -> dict[str, object]:
    counts: dict[str, int] = {}
    fields: set[str] = set()
    has_text = False
    for split in ("train", "test"):
        path = directory / f"{split}.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        counts[split] = len(rows)
        for row in rows[:100]:
            fields.update(row)
            has_text = has_text or bool(row.get("text") or row.get("tweet_text"))
    return {
        "dataset": VERSION,
        "source_url": SOURCE_URL,
        "license": LICENSE,
        "splits": counts,
        "fields": sorted(fields),
        "contains_usable_text": has_text,
        "training_status": "BLOCKED_TWEET_HYDRATION_REQUIRED" if not has_text else "READY_FOR_MAPPING",
        "label_mapping": {"flood": "FLOOD", "none": "NOT_WEATHER_RELEVANT", "fire": "EXCLUDED"},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect_dataset(args.dataset_directory)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
