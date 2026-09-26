# WeatherFusion India demonstration guide

## Start the reproducible local demo

1. Copy `.env.example` to `.env`, then run `docker compose up -d db`.
2. From `backend`, create/activate `.venv`, install `-e ".[dev]"`, and run `alembic upgrade head`.
3. From the repository root, run `backend\.venv\Scripts\python.exe scripts\seed_phase3_demo.py`.
4. Run FastAPI from `backend` with `uvicorn app.main:app --reload`; run `pnpm dev` from `frontend`.
5. Run `backend\.venv\Scripts\python.exe scripts\smoke_demo.py` once the API is available.

The seed creates clearly marked controlled demonstration records. Their content and displayed workflow outcomes are scenarios for interface testing, not genuine historical or live incidents.

## Suggested 3–5 minute flow

Open Situation to see the current report register, map context, and Open-Meteo forecast card. The card shows its source, live/cached/unavailable state, observation time, retrieval time, and a statement that forecasts are not verified ground-level incidents.

Open an event and show source provenance, geographic nearby-event search, evidence-component availability, and the separate human-review status. The evidence score ranks available support only; it does not prove the report true.

Open Review Queue, record a reasoned human action, then open the Incident Brief to show the audit trail. Use Analytics and Map to demonstrate count aggregation, filtering, clustering, and hotspots as report concentrations—not verified weather occurrence.

For an offline run, disable the network after a forecast has been cached or set `WEATHER_CONNECTOR_ENABLED=false`. The rest of the controlled demo continues; weather context displays its cached/stale state or an explicit unavailable state.

## Data boundary

Do not call the controlled social feed a live social-media integration. Do not call NOAA episode IDs duplicate-report labels. The supported NOAA experiment is historical narrative event-type classification only; see `ml/docs/NOAA_STORM_EVENTS_DATASET.md` and its generated audit/evaluation artifacts.
