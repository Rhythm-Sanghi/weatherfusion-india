# WeatherFusion India

WeatherFusion India is a Smart India Hackathon 2026 prototype for SIH 26069, the National Weather Big Data Analytics Platform. It supports controlled incident-report workflows, Open-Meteo forecast context, PostGIS operational maps, and auditable human review.

## Current status

The completion prototype includes ingestion, provenance, review/audit actions, PostGIS nearby search and aggregations, Open-Meteo live/cached forecast context, offline controlled demonstrations, and an independently evaluated NOAA historical event-type baseline.

## Ownership boundaries

- Backend, data ingestion, frontend, administration, QA, and integration are implemented in this repository.
- The evidence policy is a configurable prototype ranking mechanism, not an incident-truth model.
- NOAA ML is limited to the documented historical event-type task. It does not contribute to citizen-report truthfulness or duplicate-report claims.

## Architecture

The application is a modular monolith: FastAPI serves a versioned REST API, PostgreSQL stores application data, and React provides the operator interface. Provider contracts keep specialist verification and geospatial implementations independent from FastAPI, SQLAlchemy, and frontend models. See [architecture.md](docs/architecture.md), [integration_contracts.md](docs/integration_contracts.md), [data_sources.md](docs/data_sources.md), and [evidence_scoring_policy.md](docs/evidence_scoring_policy.md).

## Prerequisites

- Python 3.12 or newer
- Node.js 20 or newer with pnpm
- Docker Desktop with Docker Compose

## Environment

Copy `.env.example` to `.env` and adjust values for your local machine. Do not commit `.env`.

## Run PostgreSQL

```powershell
docker compose up -d db
docker compose ps
```

## Download optional spatial data

The repository deliberately excludes raw datasets and generated ML outputs so
that it stays within GitHub's normal file-size limits. The core application,
demo seed, and automated tests do not require them. To enable the optional G3
boundary overlays after cloning, download the pinned, checksum-verified files:

```powershell
python .\scripts\download_boundaries.py
```

Then apply the migrations and import the boundaries:

```powershell
python .\backend\.venv\Scripts\python.exe .\scripts\import_boundaries.py
```

The manifest and attribution documents in `datasets/india_boundaries/` identify
the exact source versions and licence obligations. NOAA source files and derived
ML data are optional research inputs; obtain them from their documented sources
and regenerate local outputs rather than committing them.

## Run the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

The health endpoint is available at `http://localhost:8000/api/health`.

## Event API

## External Weather Source

WeatherFusion uses the Open-Meteo free non-commercial Forecast API without an API key. `GET /api/v1/weather/forecast` returns forecast context for configurable coordinates (Indore by default), including temperature, relative humidity, rain, precipitation, precipitation probability, weather code, and wind speed. It preserves live/cached status, observation time, retrieval time, and cache age. Forecast context is never classified as a verified ground-level incident. Configure `WEATHER_DEFAULT_*`, `WEATHER_TIMEZONE`, `WEATHER_FORECAST_DAYS`, and `WEATHER_CONNECTOR_*` values in `.env`. `POST /api/v1/ingestion/weather` remains the separate external-observation ingestion path. Open-Meteo attribution/reference: https://open-meteo.com/en/docs.

The Phase 2 API provides `POST /api/v1/events`, `GET /api/v1/events`, `GET /api/v1/events/{event_id}`, and `GET /api/v1/events/summary`. Lists support pagination and basic event, state, severity, status, and date filters. Repeating a non-empty `external_id` for the same source returns `409 Conflict`.

Run `alembic upgrade head` after starting PostgreSQL to apply revision `20260918_01`.

## Seed the Phase 3 demo view

After the migration, run the deterministic local fixture script from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\seed_phase3_demo.py
```

It creates or updates 12 clearly labelled demo records. The status values are curated fixture data for interface testing, not verification or geospatial-provider output.

## Run the frontend

```powershell
cd frontend
pnpm install
pnpm dev
```

The frontend runs at `http://localhost:5173` by default. Situation, Events, Event Detail, and Map use `VITE_API_BASE_URL` to call the backend. Set `VITE_MAPPLS_ACCESS_TOKEN` to use the Mappls browser SDK for its India map; restrict that static token to the deployed frontend domains in the Mappls console. When it is unset or Mappls cannot load, the application uses the MapLibre fallback basemap and labels the fallback in the UI. Mappls compact views support persisted event markers; MapLibre mode also supports clusters, hotspots, and approved-boundary overlays.

## Run as a web application

The production Compose file serves the React application and API from one
origin at `http://localhost:8080`; the browser calls the API through `/api`.
It is suitable for a VM or a Docker-capable hosting service.

1. Copy `.env.production.example` to `.env.production` and replace the
   database password with a strong, unique value.

   ```text
   Copy-Item .env.production.example .env.production
   ```

2. Start the web stack:

   ```powershell
   docker compose --env-file .env.production -f compose.production.yaml up --build -d
   ```

3. Open `http://localhost:8080`. The API health endpoint is available at
   `http://localhost:8080/api/health`.

The backend container applies database migrations before it starts. For a
public deployment, put the service behind HTTPS and restrict any Mappls browser
token to the final domain. Optional boundary overlays require the download and
import steps described above.

## Validate the foundation

```powershell
# Backend, from backend/
ruff check .
pytest
alembic current

# Frontend, from frontend/
pnpm typecheck
pnpm lint
pnpm test
pnpm build

# Compose, from the repository root
docker compose config
```

GitHub Actions runs the backend and frontend checks on every push and pull
request. The PostGIS integration tests require a locally prepared database with
the demo seed and boundary import, so run them before releases using the setup
steps above.

## Provider architecture

Provider contracts live in `backend/app/domain/providers.py`. The factories in `backend/app/api/dependencies.py` select implementations using `VERIFICATION_PROVIDER` and `GEOSPATIAL_PROVIDER`. See [integration_contracts.md](docs/integration_contracts.md) before implementing a teammate provider.

## Repository layout

```text
backend/   FastAPI, SQLAlchemy, Alembic, tests, provider contracts
frontend/  React, TypeScript, Vite operator-console shell
docs/      Architecture, provider contracts, and status model
demo/      Reserved for deterministic fixtures and scenarios
scripts/   Reserved for development and demo commands
```

## Scope boundary

The prototype does not claim automated incident truth, verified duplicate labels, live social-media collection, or calibrated evidence probabilities. Forecasts are contextual model data, not ground-level incident observations. See [completion_blueprint.md](docs/completion_blueprint.md), [data_sources.md](docs/data_sources.md), and [evidence_scoring_policy.md](docs/evidence_scoring_policy.md).

## Offline demo mode and optional ML

Set `DEMO_MODE=true` to prevent live Open-Meteo calls while retaining the same controlled-report, review, audit, map, and analytics flow. Seed the deterministic demo data first with `scripts/seed_phase3_demo.py`.

The runtime default verification provider is `mock`. The included `.env.example` explicitly selects the model-free `operational` provider and PostGIS for a local operational-style configuration. To use a reviewed local text model, set `VERIFICATION_PROVIDER=ml` and `VERIFICATION_MODEL_ARTIFACT_PATH` to an artifact produced by `ml/weather_classifier.py`. The artifact provider records its dataset hash, model version, predicted category, and uncalibrated decision margin; it never declares a report true or changes human status.
## Controlled social-weather feed

WeatherFusion India includes a controlled social-weather feed connector for demonstrating hashtag-based ingestion without commercial social-media credentials or live-platform claims. It filters a deterministic prototype dataset, preserves raw source records and provenance, and supports metadata-only image/video evidence. Authorized live platform integrations can replace the connector through the same boundary later.

## PostGIS spatial infrastructure and G2 queries

The database uses `postgis/postgis:16-3.4` with PostgreSQL 16 and a separate persistent PostGIS volume. `weather_events.location` is a stored `geography(Point, 4326)` generated from the existing `longitude, latitude` fields, with a partial GiST index. Run `backend/.venv/Scripts/python.exe -m alembic upgrade head` after restoring a verified logical backup.

Set `GEOSPATIAL_PROVIDER=postgis` in `.env` to enable the real provider. It powers
`GET /api/v1/events/{event_id}/nearby` (default 5,000 metres; maximum 100,000) and
`GET /api/v1/events/map/events`, which returns a GeoJSON FeatureCollection with
`[longitude, latitude]` point coordinates. If PostGIS is unavailable, those read-only
endpoints return a clear service-unavailable response and the event register stays usable.
G2 does not provide administrative-boundary enrichment, clustering, hotspots, or GIS-based
verification conclusions; boundary work is deferred to G3.

## G3 geographic aggregation

G3 adds `GET /api/v1/geo/clusters`, `GET /api/v1/geo/hotspots`, and
`GET /api/v1/geo/regions/summary`. Clusters use PostGIS `ST_ClusterDBSCAN` on EPSG:6933
projected metre coordinates; hotspots use a reproducible EPSG:6933 fixed-metre grid. Both
describe concentrations of submitted reports, never verified weather occurrence. Regional
summaries can use source-provided state/district fields or the imported administrative-boundary
dataset. `GET /api/v1/geo/boundaries` exposes the approved boundary metadata and the regional
summary response identifies its grouping method and dataset vintage. These overlays are spatial
context only, not a legal boundary determination.
