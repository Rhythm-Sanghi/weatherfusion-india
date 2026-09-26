# WeatherFusion India architecture

WeatherFusion is a modular-monolith prototype with a FastAPI API, PostgreSQL/PostGIS data store, and React operator console. It preserves source records before normalization and keeps source provenance, system evidence, and human review as separate concerns.

```text
Controlled reports / controlled feed / Open-Meteo forecast
                         |
                 validation + provenance
                         |
              PostgreSQL + PostGIS geometry
                   |                 |
          evidence-ranking policy   geographic queries
                   |                 |
             FastAPI REST API -> React operator console
                                      |
                             human review + audit trail
```

## Data and provider boundaries

- Open-Meteo is the only live external provider. Its forecast context is configurable by coordinates, cached locally for offline demonstrations, and explicitly never treated as a verified ground observation.
- NOAA Storm Events records are historical data held outside application event records. The supported narrative event-type experiment has its own provenance, grouped split, and evaluation artifacts under `ml/`.
- Controlled citizen reports and the controlled social feed are synthetic demonstrations. They carry explicit provenance and are never represented as live social posts or historical incidents.
- `VerificationProvider` applies an explainable evidence-ranking policy. It can prioritize review, but cannot verify or reject a report. `GeospatialProvider` uses PostGIS for nearby search, maps, clusters, hotspots, and approved-boundary containment.
- The frontend uses the Mappls browser SDK only when `VITE_MAPPLS_ACCESS_TOKEN` is configured; its compact map surface intentionally supports persisted event markers only. The MapLibre fallback supports the additional spatial overlays. Browser map tokens must be restricted to the deployed frontend domains.

## Evidence and review

Evidence components are configurable: source reliability (25%), independent corroboration (25%), official observations (20%), location/time consistency (15%), and validated ML evidence (15%). Missing evidence is shown as unavailable and weights are normalized only across available components. A score means stronger available support under this policy; it is not a calibrated probability or a conclusion that an incident occurred.

Human reviewers remain the only authority for `VERIFIED`, `REJECTED`, and `ESCALATED` outcomes. The audit trail records those decisions independently of the system assessment.

## Offline operation

The local demo database, controlled fixtures, and cached Open-Meteo responses are sufficient for the core flow without external connectivity. A failed live request returns cached data with the original observation/retrieval times and stale status, or an explicit unavailable result; it never substitutes synthetic values labeled as live.
