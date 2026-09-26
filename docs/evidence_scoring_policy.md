# WeatherFusion prototype evidence-ranking policy

## Purpose

This policy ranks the strength of currently available supporting evidence so an operator can prioritize review. It is not a calibrated probability that an incident occurred, and it never changes human-review status by itself.

## Configurable weights

| Evidence channel | Default weight | Current status |
| --- | ---: | --- |
| Source reliability | 25% | Available only when the source has a documented reliability profile |
| Independent corroboration | 25% | Available when independent source records support the same event type within the configured time and location window |
| Official weather observations | 20% | Available when a nearby, time-aligned Open-Meteo observation has been ingested; otherwise explicitly unavailable |
| Location and time consistency | 15% | Available when report coordinates and observed time pass the configured plausibility window |
| Validated ML evidence | 15% | Available only when the artifact-backed ML provider is selected and supplies a matching event type |

The values are configured with `EVIDENCE_*` environment settings. Startup rejects a configuration whose five weights do not total 1.0.

## Missing-evidence policy

The system calculates two distinct measures:

- **Evidence score**: weighted support normalized over channels that were actually available.
- **Evidence coverage**: the configured weight represented by available channels.

Unavailable channels add neither support nor a fabricated zero. They are shown explicitly with a reason code. A score with low coverage remains `NEEDS_REVIEW`; it does not become corroborated merely because its limited available evidence is strong.

Coverage depends on the evidence actually present. A score below the configured coverage threshold remains `NEEDS_REVIEW`; a score never changes the human-review status.

## Corroboration rules

Independent corroboration counts distinct source IDs, not the number of records. Candidate records must be within the configured PostGIS distance/time window and have the same event type. Related records are evidence references only; they are never automatically merged, removed, or used as a human disposition.

Conflicting nearby event types are exposed as a reason for review. They do not establish that the report is false.

## Official and ML evidence

Official-observation evidence is included only when an ingested Open-Meteo current-weather observation is inside the configured radius and a three-hour time window. A matching event type supports triage; a mismatch is displayed as conflicting evidence. Cached records retain source, observation time, retrieval time, cache age, and cached status.

ML contributes only after the artifact-backed provider is configured with a documented, appropriate training corpus, evaluation, held-out test set, dataset hash, and model version. It exposes an uncalibrated decision margin, never a probability that a reported incident occurred.

## Operator display

Event Detail and Review Workspace display the system assessment separately from the human-review status. They show score, coverage, each channel's availability, weighted contribution, and reason codes. All pages must state that automated signals prioritize review and do not establish incident truth.
