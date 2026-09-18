# WeatherFusion India Architecture

WeatherFusion India is a modular monolith for SIH 26069, the National Weather Big Data Analytics Platform. The prototype prioritizes one reliable path from report intake to human-reviewed operational information while retaining integration seams for specialist modules.

## Current architecture

```text
Inputs -> validation and normalization -> PostgreSQL -> processing orchestration
                                                      |             |
                                          VerificationProvider  GeospatialProvider
                                                      |             |
                                              REST API -> React operator console
```

The FastAPI backend has API, core, domain, database, ingestion, repository, service, and integration boundaries. The React application has centralized API access, route-level pages, reusable layout components, and feature folders. PostgreSQL is the development database; SQLAlchemy and Alembic provide the persistence and migration foundation.

## Provider boundaries

AI/ML verification and geospatial/data engineering are teammate-owned. The backend owns provider contracts and composition, while provider implementations remain replaceable by configuration. Phase 1 mock providers intentionally return unavailable or empty results only.

Machine assessment and human disposition are separate status dimensions. A provider can help prioritize a report but cannot verify or reject it on behalf of an administrator.

## REST API

The foundation exposes `GET /api/health` plus Phase 2 event endpoints under `/api/v1/events`. The ingestion service persists a canonical event and raw payload before invoking optional provider interfaces. Provider failure leaves the event stored with `PARTIAL` processing and an unavailable or pending assessment. Review, map, and analytics endpoints remain deferred.

## Future evolution

National-scale components such as event streaming, distributed processing, object storage, production ML inference, and GIS infrastructure are a roadmap, not Phase 1 capabilities. They can be introduced after the prototype has a proven end-to-end workflow and stable contracts.
