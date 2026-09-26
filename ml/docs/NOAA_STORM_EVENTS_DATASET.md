# NOAA Storm Events dataset assessment

## Source and scope

This project received ten NOAA Storm Events detail CSV files for 1950–1959. The preprocessing command records each original filename, SHA-256 digest, byte count, modified time, schema, and record count in `ml/data/noaa_storm_events_1950_1959/source_manifest.json`.

The source is the NOAA National Centers for Environmental Information Storm Events Database. The source URL is recorded in the generated manifest. The filenames identify `ftp_v1.0` and contain a `cYYYYMMDD` revision/date token. That token is retained as source provenance but is not presented as the download date. The actual download date is unknown unless the downloader supplies it with `--download-date YYYY-MM-DD`.

The original files under `datasets/NOAA_Strom_Events/` are inputs only. The preprocessing program never writes to, renames, or alters them.

## Reproduction

From the repository root, run:

```powershell
python .\ml\prepare_noaa_storm_events.py `
  .\datasets\NOAA_Strom_Events `
  .\ml\data\noaa_storm_events_1950_1959 `
  --download-date YYYY-MM-DD
```

If the verified download date is unavailable, omit `--download-date`. The manifest will state `UNKNOWN_NOT_EMBEDDED_IN_FILES` rather than invent a date.

## Derived outputs

- `source_manifest.json`: source provenance and file hashes.
- `audit_report.json`: aggregate audit, data adequacy findings, and output counts.
- `task_adequacy.json`: machine-readable list of supported and unsupported ML tasks.
- `record_audit.csv`: one audit row per original source record, referenced by source file and source line.
- `structured_event_type_candidates_not_for_text_ml.csv`: source-preserving rows with valid start time/coordinates and a NOAA event-type label. It is a registry for assessment, not a training dataset for the WeatherFusion report-text classifier.

No `train.csv`, `validation.csv`, `test.csv`, model artifact, or precision/recall/F1 report is written unless a future source has both legitimate input text and an incident-aware/episode-aware grouping key.

## What this collection can and cannot support

It can support descriptive analysis of NOAA-recorded event types and a source-preserving audit of historical records.

It cannot support the WeatherFusion report-text event-type classifier when all supplied narrative fields are blank. It also cannot support an episode-aware or incident-aware split when every supplied `EPISODE_ID` is blank. Splitting on `EVENT_ID` would only create one-record groups and would not prevent related events from leaking across train and test. The preprocessing process intentionally does not invent proxy incident groups.

NOAA `EVENT_TYPE` is a legitimate source label for its own historical event record. It is not a false-report label, a truthfulness label, or a verified duplicate-report label. An NOAA episode identifier must never be described as a duplicate-report label.

## Future data requirements

To train and evaluate the intended report-text model, add an authorised dataset that supplies:

1. genuine event/report narratives;
2. a documented event-type label taxonomy and mapping to WeatherFusion categories;
3. a legitimate incident or episode grouping key for leakage-resistant train/validation/test splits;
4. source licence, URL, retrieval date, and provenance; and
5. enough held-out records per class to report precision, recall, and F1 responsibly.

To train duplicate detection, add independently reviewed duplicate/non-duplicate pair labels. Do not derive them from NOAA episode identifiers.

## Approved 2025 historical event-type experiment

An additional official NOAA detail download is preserved unchanged at
`datasets/NOAA_Storm_Events_2025/StormEvents_details-ftp_v1.0_d2025_c20260819.csv.gz`.
It was retrieved on 2026-09-24 from the NOAA bulk directory. Its SHA-256, record
count, source URL, file revision token, source schema, and audit are recorded in
`ml/data/noaa_storm_events_2025/source_manifest.json` and `audit_report.json`.

Reproduce its preparation and evaluation from the repository root:

```powershell
python .\ml\prepare_noaa_storm_events.py .\datasets\NOAA_Storm_Events_2025 .\ml\data\noaa_storm_events_2025 --download-date 2026-09-24
python .\ml\train_noaa_event_type_classifier.py .\ml\data\noaa_storm_events_2025 .\ml\artifacts\noaa_event_type_2025
```

The cleaner retains all source/provenance fields and audit flags. It accepts a
record for text classification only when it has a NOAA event-type label, begin
timestamp, source event ID, event narrative, and episode ID. Invalid coordinates
are audited but do not discard an otherwise usable text input. Episode IDs are
used only to keep related NOAA events in one split; they are never duplicate
labels.

The generated data contains 72,360 original records, 61,615 eligible narrative
records, and deterministic episode-aware train/validation/test partitions of
50,026 / 5,665 / 5,924 records. `evaluation.json` reports the held-out NOAA
event-type metric (micro precision, recall, and F1) with per-class support. The
baseline result does not evaluate citizen-report truthfulness, false reports, or
duplicate reports, and it must not be used as evidence that a new incident occurred.
