# WeatherFusion India

WeatherFusion India is a Smart India Hackathon 2026 prototype for SIH 26069, the National Weather Big Data Analytics Platform. It will unify weather reports from multiple sources, present operational information to analysts, and preserve human review decisions with an audit trail.

## Current status

Phase 3 adds the first operator vertical: a national situation view, event explorer, event detail, and display-only event map backed by the event API.

## Ownership boundaries

- Backend, data ingestion, frontend, administration, QA, and integration are implemented in this repository.
- AI/ML Verification Provider is teammate-owned.
- Geospatial Provider is teammate-owned.

Temporary mock adapters exist only to allow dependency injection and contract development. They do not classify, score, detect duplicates, geocode, calculate distance, cluster, or analyze data.

## Architecture

The application is a modular monolith: FastAPI serves a versioned REST API, PostgreSQL stores application data, and React provides the operator interface. Provider contracts keep specialist verification and geospatial implementations independent from FastAPI, SQLAlchemy, and frontend models. See [architecture.md](docs/architecture.md) and [integration_contracts.md](docs/integration_contracts.md).

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

The frontend runs at `http://localhost:5173` by default. Situation, Events, Event Detail, and Map use `VITE_API_BASE_URL` to call the backend. The map uses a public MapLibre demo basemap and presents a clear notice if it is unavailable.

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

## Phase boundary

Phase 3 is limited to display and navigation. It does not implement review actions, audit logging, provider intelligence, advanced analytics, or geospatial analysis.
