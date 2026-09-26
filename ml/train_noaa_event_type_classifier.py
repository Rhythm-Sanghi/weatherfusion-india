"""Train and evaluate a provenance-preserving NOAA narrative event-type baseline.

This is deliberately a small, inspectable multinomial Naive-Bayes baseline. It
reports precision, recall and F1 only because NOAA EVENT_TYPE supplies the
ground-truth label and the prepared input includes a held-out, episode-grouped
test partition. It is a historical event-type experiment, not a detector of
whether a citizen report is true.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TOKEN = re.compile(r"[\w']+", re.UNICODE)


def tokenize(value: str) -> list[str]:
    return TOKEN.findall(value.casefold())


def load_jsonl(path: Path) -> list[dict[str, str]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def narrative(row: dict[str, str]) -> str:
    return " ".join(part for part in (row.get("EVENT_NARRATIVE", ""), row.get("EPISODE_NARRATIVE", "")) if part.strip())


def train(rows: list[dict[str, str]]) -> dict[str, Any]:
    document_counts: Counter[str] = Counter()
    word_counts: dict[str, Counter[str]] = defaultdict(Counter)
    token_totals: Counter[str] = Counter()
    vocabulary: set[str] = set()
    for row in rows:
        label = row["EVENT_TYPE_NORMALIZED"]
        bag = tokenize(narrative(row))
        document_counts[label] += 1
        word_counts[label].update(bag)
        token_totals[label] += len(bag)
        vocabulary.update(bag)
    vocabulary_size = max(1, len(vocabulary))
    document_total = sum(document_counts.values())
    # Precompute the logarithms used at prediction time. This avoids millions
    # of repeated math.log calls while retaining the exact same Laplace-smoothed
    # multinomial Naive-Bayes decision rule.
    base_scores = {
        label: math.log(count / document_total)
        for label, count in document_counts.items()
    }
    token_scores = {
        label: {token: math.log(count + 1) for token, count in counts.items()}
        for label, counts in word_counts.items()
    }
    return {
        "document_counts": document_counts,
        "word_counts": word_counts,
        "token_totals": token_totals,
        "vocabulary": vocabulary,
        "base_scores": base_scores,
        "token_scores": token_scores,
    }


def predict(model: dict[str, Any], value: str) -> str:
    labels = sorted(model["document_counts"])
    token_list = tokenize(value)
    scores: dict[str, float] = {}
    for label in labels:
        denominator_log = math.log(model["token_totals"][label] + len(model["vocabulary"]))
        score = model["base_scores"][label] - len(token_list) * denominator_log
        token_score = model["token_scores"][label]
        for token in token_list:
            score += token_score.get(token, 0.0)
        scores[label] = score
    return min(scores, key=lambda label: (-scores[label], label))


def metrics(rows: list[dict[str, str]], model: dict[str, Any]) -> dict[str, Any]:
    confusion: Counter[tuple[str, str]] = Counter()
    for row in rows:
        actual = row["EVENT_TYPE_NORMALIZED"]
        confusion[actual, predict(model, narrative(row))] += 1
    labels = sorted({actual for actual, _ in confusion} | {predicted for _, predicted in confusion})
    per_class: dict[str, dict[str, float | int]] = {}
    total_true_positive = total_false_positive = total_false_negative = 0
    for label in labels:
        true_positive = confusion[label, label]
        false_positive = sum(confusion[actual, label] for actual in labels if actual != label)
        false_negative = sum(confusion[label, predicted] for predicted in labels if predicted != label)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        support = sum(confusion[label, predicted] for predicted in labels)
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
        total_true_positive += true_positive
        total_false_positive += false_positive
        total_false_negative += false_negative
    precision = total_true_positive / (total_true_positive + total_false_positive) if total_true_positive + total_false_positive else 0.0
    recall = total_true_positive / (total_true_positive + total_false_negative) if total_true_positive + total_false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "sample_count": len(rows),
        "micro_precision": precision,
        "micro_recall": recall,
        "micro_f1": f1,
        "per_class": per_class,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    dataset_dir = args.dataset_dir.resolve()
    partitions = {name: load_jsonl(dataset_dir / f"{name}.jsonl") for name in ("train", "validation", "test")}
    if not all(partitions.values()):
        raise SystemExit("Expected non-empty train, validation and test episode-aware partitions.")
    model = train(partitions["train"])
    result = {
        "task": "NOAA historical narrative event-type classification",
        "ground_truth": "NOAA Storm Events EVENT_TYPE",
        "split_policy": "Episodes are deterministically assigned before training; EPISODE_ID is used solely to prevent leakage and is not a duplicate-report label.",
        "dataset_sha256": hashlib.sha256((dataset_dir / "event_type_text_candidates.jsonl").read_bytes()).hexdigest(),
        "split_counts": {name: len(rows) for name, rows in partitions.items()},
        "validation": metrics(partitions["validation"], model),
        "held_out_test": metrics(partitions["test"], model),
        "limitations": [
            "Historical NOAA event-type labels do not establish whether a new citizen report is true.",
            "This CPU baseline returns class decisions, not calibrated probabilities.",
            "Do not use this result as duplicate-report or truthfulness evaluation.",
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "evaluation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact = {
        "format": "weatherfusion-noaa-multinomial-naive-bayes-v1",
        "task": result["task"],
        "dataset_sha256": result["dataset_sha256"],
        "labels": sorted(model["document_counts"]),
        "limitations": result["limitations"],
    }
    (args.output_dir / "model_manifest.json").write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"test_micro_f1": result["held_out_test"]["micro_f1"], "splits": result["split_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
