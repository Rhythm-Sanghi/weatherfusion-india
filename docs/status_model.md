# WeatherFusion Status Model

WeatherFusion records three independent status dimensions. Keeping them separate prevents an automated result from being presented as a human decision.

| Dimension | Values | Meaning |
| --- | --- | --- |
| `processing_status` | `RECEIVED`, `PROCESSING`, `COMPLETE`, `PARTIAL`, `FAILED` | Technical progress through ingestion and optional enrichment. |
| `system_assessment` | `PENDING`, `CORROBORATED`, `NEEDS_REVIEW`, `DISPUTED`, `UNAVAILABLE` | Current automated/provider assessment. It is evidence, never a final truth claim. |
| `admin_status` | `UNREVIEWED`, `VERIFIED`, `REJECTED`, `ESCALATED` | A human reviewer disposition. |

An event initially enters as `RECEIVED`, `PENDING`, and `UNREVIEWED`. Processing can become `COMPLETE` or `PARTIAL` independently of whether a provider is available. A provider can return `UNAVAILABLE` without invalidating the stored event. Only a human review action can move `admin_status` away from `UNREVIEWED`.

Later phases will validate permitted transitions and write audit history. Phase 1 defines the vocabulary only.
