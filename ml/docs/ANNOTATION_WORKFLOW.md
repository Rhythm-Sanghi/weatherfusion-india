# Local annotation workflow

1. Copy `ml/templates/annotation_queue_template.csv` or `.jsonl`, replace the example row with lawfully obtained text, and run `python ml/import_annotation_queue.py INPUT.csv ml/data/input/annotation_queue.jsonl`. The importer preserves provenance and records an original source label only as unreviewed notes.
2. Start `python ml/annotation_app.py`. It binds only to `127.0.0.1:8765` and writes reviewed labels to `ml/data/annotations/reviewed.jsonl`.
3. Every annotation must select weather relevance, a supported event type when relevant, an annotator ID, and optional incident/duplicate group identifiers. `UNCERTAIN` and unsupported examples must not receive an event type.
4. A second accountable reviewer changes validated records from `REVIEWED` to `APPROVED`; the application never performs this transition.
5. A reviewer can export approved records to `ml/data/annotations/approved.jsonl`. Validate with `python ml/validate_dataset.py ml/data/annotations/approved.jsonl --approved-only`, then run `python ml/training_readiness.py ml/data/annotations/approved.jsonl`. Train only after each supported class has adequate independent incidents in train and test.

The current repository has no authorised queue records and no approved real text labels. Do not use the synthetic fixtures for annotation metrics or training.
