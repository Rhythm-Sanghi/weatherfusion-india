# ML and verification status

## Citizen-report review

`VERIFICATION_PROVIDER=operational` selects a model-free provider. It records
an untrained classification state and related-report evidence from persisted
reports. Independent same-type reports within 20 km and 24 hours can support
triage; absent or conflicting evidence remains `NEEDS_REVIEW`. It does not
establish incident truth, merge events or make human-review decisions.

The synthetic annotation fixtures are not a trained citizen-report classifier
or an evaluation corpus. Annotation tooling rejects the pending fixtures for
training. A reviewed report-text corpus is still needed for that task.

## Historical NOAA experiment

The repository includes preparation and evaluation tooling for a separate NOAA
2025 narrative event-type baseline, with its documented episode-grouped split.
This task has a different scope from operational citizen-report review. See
[NOAA_STORM_EVENTS_DATASET.md](NOAA_STORM_EVENTS_DATASET.md) for reproduction,
the historical 1950–1959 input assessment and the 2025 experiment.

Raw inputs, generated partitions, model artifacts and evaluation outputs are
not distributed in Git. Recreate them from the documented sources. Historical
classification results do not measure false reports or duplicate reports.

## Explicit artifact provider

The optional `ml` provider loads the artifact named by
`VERIFICATION_MODEL_ARTIFACT_PATH`; it is not enabled by the model-free default
configuration. A predicted category and uncalibrated decision margin are model
outputs, not authority to mark an incident verified.

Prepare approved annotations with `ml/validate_dataset.py` and
`ml/prepare_dataset.py`. Preserve source licences, provenance and grouping rules;
do not train or evaluate on synthetic fixture records as real-world evidence.
