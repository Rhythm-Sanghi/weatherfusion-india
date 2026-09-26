"""Report whether approved human annotations can support weather-model evaluation."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

TOKEN = re.compile(r"\w+", re.UNICODE)


def report(path: Path) -> dict[str, object]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    approved = [row for row in rows if row.get("annotation_status") == "APPROVED" and not row.get("synthetic_fixture")]
    texts = Counter(" ".join(TOKEN.findall(str(row.get("report_text", "")).casefold())) for row in approved)
    relevance = Counter(str(row.get("weather_relevance_label")) for row in approved)
    event_types = Counter(str(row.get("primary_event_type_label")) for row in approved if row.get("primary_event_type_label"))
    groups = {str(row.get("incident_group_id")) for row in approved if row.get("incident_group_id")}
    insufficient = sorted(label for label, count in event_types.items() if count < 20)
    return {"approved_records": len(approved), "weather_relevance_distribution": dict(relevance), "event_type_distribution": dict(event_types), "independent_incident_groups_known": len(groups), "exact_duplicate_text_records": sum(count - 1 for count in texts.values() if count > 1), "residual_leakage_risk": "incident groups are absent for some records" if len(groups) < len(approved) else "known incident groups available", "classes_not_meaningfully_evaluable": sorted({"WEATHER_RELEVANT", "NOT_WEATHER_RELEVANT", *event_types} - {label for label, count in relevance.items() if count >= 20} - {label for label, count in event_types.items() if count >= 20}), "event_types_below_20_examples": insufficient}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("annotations", type=Path); args = parser.parse_args(); print(json.dumps(report(args.annotations), indent=2, sort_keys=True))
