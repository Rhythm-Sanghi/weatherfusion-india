# Dataset research and acquisition record

## CREXWET v1

- Publisher: Barcelona Supercomputing Center / CREXDATA; [primary Zenodo record](https://zenodo.org/records/17950332).
- Retrieved: 2026-09-20. Archive SHA-256: `ff1be9bca827b54fbb623b88c40ad007d479d2207af302d4039a358fd6ce6ecc`.
- Licence: CC BY 4.0. The cached archive is ignored by Git; derived use must preserve attribution and licence notices.
- Purpose: tweet classification for flood, wildfire, or neither. The record reports 592,704 train and 34,722 test instances; the test incidents are disjoint from train and human-reviewed after machine labelling.
- Fields actually obtained: identifier, tweet identifier, language, label, label quality. There is no text field in the downloaded JSONL. The publisher states that tweet text must be downloaded from Twitter/X and may be unavailable when deleted.
- Mapping: `flood` → `FLOOD`; `none` → weather-not-relevant; `fire` is excluded because WeatherFusion has no wildfire class. Generic storm, forecast, and other disaster labels are not mapped.
- Result: **blocked for local real-model training**. Hydrating full text needs a lawful Twitter/X access route and terms review. No hydration was attempted and no tweet text was stored.

## Rejected alternatives

- [HumAID](https://crisisnlp.qcri.org/humaid_dataset.html) is English, human-annotated, and CC BY-NC-SA 4.0, but its labels are humanitarian-information categories rather than weather type. It cannot directly train this task.
- [CrisisNLP](https://crisisnlp.qcri.org/) contains useful crisis corpora but many releases are tweet IDs or category labels unrelated to weather type. Its terms must be reviewed before use.

The downloaded CREXWET archive is suitable as a provenance-checked acquisition record, but not evidence of trained-model performance.
