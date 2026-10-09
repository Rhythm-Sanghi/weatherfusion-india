# WeatherFusion India

A Smart India Hackathon 2026 prototype for SIH 26069. It combines incident-report
ingestion, operator review, a PostGIS map and Open-Meteo forecast context.
FastAPI serves the API; React provides the operator interface.

Controlled reports are demonstration data. Forecasts are context, not proof of
a ground-level incident. Human review remains separate from automated evidence
ranking. The optional historical NOAA classification experiment evaluates event
types, not citizen-report truthfulness or duplicate detection.

## Local setup

Requires Python 3.12+, Node 20+ with pnpm, and Docker Compose. From the repository
root, copy `.env.example` to `.env` and start PostgreSQL:

```powershell
docker compose up -d db
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

In another terminal, from the repository root:

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open http://localhost:5173. The API health endpoint is
http://localhost:8000/api/health. Use `VITE_API_BASE_URL` for a different API host.

To seed the controlled demo, run from the root:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\seed_phase3_demo.py
```

For optional boundary overlays, download the pinned files and import them after
migrations and backend installation:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\download_boundaries.py
.\backend\.venv\Scripts\python.exe .\scripts\import_boundaries.py
```

Source versions and attribution are in `datasets/india_boundaries/`. Raw datasets,
generated splits and model outputs are ignored by Git and recreated locally.

## Application behavior

- Event registration, filtering, provenance, review queue and audit trail.
- Open-Meteo live/cached forecast context with source and retrieval timestamps.
- PostGIS nearby-event queries, clustering, hotspots and regional counts. These
  describe report concentrations, not verified weather occurrence.
- Optional Mappls browser basemap; MapLibre fallback when it is unavailable.
- Controlled citizen/social-report demonstrations and offline operation with
  `DEMO_MODE=true` after seeding. Controlled feeds are not live social ingestion.

The example environment selects the model-free `operational` verification
provider and PostGIS. Runtime defaults and explicit artifact-based alternatives
are described in [ML status](ml/docs/OPERATIONAL_STATUS.md) and
[integration contracts](docs/integration_contracts.md).

## Web deployment

Copy `.env.production.example` to `.env.production`, replace the database
password, then:

```powershell
docker compose --env-file .env.production -f compose.production.yaml up --build -d
```

Open http://localhost:8080. Public deployment requires HTTPS and an appropriate
access configuration. Restrict any Mappls browser token to the deployed domains.
The container applies migrations on startup; back up persistent data before upgrades.

## Checks and documentation

From `backend`: `ruff check .`, `pytest`, `alembic current`.
From `frontend`: `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build`.
PostGIS integration checks require the prepared database and optional boundaries.

- [Architecture](docs/architecture.md) and [provider contracts](docs/integration_contracts.md)
- [Data sources](docs/data_sources.md), [evidence policy](docs/evidence_scoring_policy.md) and [status model](docs/status_model.md)
- [Demo guide](docs/demo_guide.md)
- [NOAA dataset experiments](ml/docs/NOAA_STORM_EVENTS_DATASET.md)
- [Contributing](CONTRIBUTING.md)
