# ML operational status

WeatherFusion includes annotation validation and source-aware manifest preparation. It has no approved labelled training corpus or trained classifier. The three fixture records are synthetic and pending; tooling rejects them for training.

Set `VERIFICATION_PROVIDER=operational` to enable the local, explainable provider. It records an untrained classification state, bounded related-report candidates, and verification evidence from persisted reports. It never changes source event types, merges events, or makes human-review decisions.

The provider considers only independent canonical reports within 20 km and 24 hours. Same-type reports become corroborating operational evidence; nearby different types and absent evidence remain `NEEDS_REVIEW`. This is a review-triage signal, not proof of an incident.

To prepare approved labels:

```powershell
python ml/validate_dataset.py path/to/labels.jsonl
python ml/prepare_dataset.py path/to/labels.jsonl ml/output
```

Use a reviewed source dataset with documented licence and provenance before training or evaluating a supervised classifier. Do not use the synthetic fixtures for either purpose.
