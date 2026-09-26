"""Reproducible local baseline for approved WeatherFusion annotations.

The implementation uses only the Python standard library so an authorized
corpus can be trained on CPU without a cloud service or GPU. Scores returned
by this baseline are Naive-Bayes decision scores, not calibrated probabilities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

TOKEN = re.compile(r"[\w']+", re.UNICODE)
SUPPORTED = {"HEAVY_RAINFALL", "FLOOD", "THUNDERSTORM", "HEATWAVE", "FOG", "DUST_STORM", "STRONG_WIND"}


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.casefold())


def load_approved(path: Path) -> list[dict[str, object]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    accepted: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        text = row.get("report_text")
        if row.get("annotation_status") != "APPROVED" or row.get("synthetic_fixture"):
            continue
        if not isinstance(text, str) or not text.strip() or row.get("weather_relevance_label") not in {"WEATHER_RELEVANT", "NOT_WEATHER_RELEVANT"}:
            continue
        fingerprint = hashlib.sha256(" ".join(tokens(text)).encode()).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        accepted.append(row)
    if not accepted:
        raise ValueError("No approved, non-synthetic, text-labelled records available.")
    return accepted


def split(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {"train": [], "validation": [], "test": []}
    for row in rows:
        group = str(row.get("incident_group_id") or row.get("duplicate_group_id") or row["record_id"])
        bucket = int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) % 100
        result["train" if bucket < 80 else "validation" if bucket < 90 else "test"].append(row)
    return result


def train(rows: list[dict[str, object]], dataset_sha256: str) -> dict[str, object]:
    labels = [str(row["weather_relevance_label"]) for row in rows]
    counts = Counter(labels)
    vocabulary: set[str] = set()
    words: dict[str, Counter[str]] = defaultdict(Counter)
    totals: Counter[str] = Counter()
    for row, label in zip(rows, labels, strict=True):
        bag = tokens(str(row["report_text"]))
        words[label].update(bag); totals[label] += len(bag); vocabulary.update(bag)
    type_rows = [row for row in rows if row["weather_relevance_label"] == "WEATHER_RELEVANT" and row.get("primary_event_type_label") in SUPPORTED]
    type_counts: Counter[str] = Counter(); type_words: dict[str, Counter[str]] = defaultdict(Counter); type_totals: Counter[str] = Counter(); type_vocabulary: set[str] = set()
    for row in type_rows:
        label = str(row["primary_event_type_label"]); bag = tokens(str(row["report_text"]))
        type_counts[label] += 1; type_words[label].update(bag); type_totals[label] += len(bag); type_vocabulary.update(bag)
    artifact = {"format": "weatherfusion-naive-bayes-v1", "model_version": "naive-bayes-v1", "dataset_sha256": dataset_sha256, "supported_event_types": sorted(type_counts), "relevance": {"counts": dict(counts), "words": {key: dict(value) for key, value in words.items()}, "totals": dict(totals), "vocabulary": sorted(vocabulary)}, "limitations": ["Uncalibrated Naive-Bayes decision scores", "Training corpus provenance is stored in dataset_sha256"]}
    if type_counts:
        artifact["event_type"] = {"counts": dict(type_counts), "words": {key: dict(value) for key, value in type_words.items()}, "totals": dict(type_totals), "vocabulary": sorted(type_vocabulary)}
    return artifact


def predict(artifact: dict[str, object], text: str) -> tuple[str, float]:
    if not text.strip(): return "UNKNOWN", 0.0
    relevance = artifact["relevance"]
    assert isinstance(relevance, dict)
    counts, words, totals, vocabulary = relevance["counts"], relevance["words"], relevance["totals"], relevance["vocabulary"]
    assert isinstance(counts, dict) and isinstance(words, dict) and isinstance(totals, dict) and isinstance(vocabulary, list)
    total_docs = sum(int(value) for value in counts.values()); vocabulary_size = max(1, len(vocabulary))
    scores: dict[str, float] = {}
    for label, count in counts.items():
        bag = words[str(label)]; assert isinstance(bag, dict)
        score = math.log(int(count) / total_docs)
        for token in tokens(text): score += math.log((int(bag.get(token, 0)) + 1) / (int(totals[str(label)]) + vocabulary_size))
        scores[str(label)] = score
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    margin = ordered[0][1] - ordered[1][1] if len(ordered) > 1 else ordered[0][1]
    return ("WEATHER_RELEVANT" if ordered[0][0] == "WEATHER_RELEVANT" and margin > 0 else "UNKNOWN", margin)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("annotations", type=Path); parser.add_argument("artifact", type=Path)
    arguments = parser.parse_args(); rows = load_approved(arguments.annotations); partitions = split(rows)
    if not partitions["train"] or not partitions["test"]: raise ValueError("Split does not contain both train and held-out test records.")
    digest = hashlib.sha256(arguments.annotations.read_bytes()).hexdigest(); artifact = train(partitions["train"], digest)
    artifact["split_counts"] = {name: len(items) for name, items in partitions.items()}; arguments.artifact.parent.mkdir(parents=True, exist_ok=True)
    arguments.artifact.write_text(json.dumps(artifact, sort_keys=True), encoding="utf-8"); print(json.dumps(artifact["split_counts"], sort_keys=True))
