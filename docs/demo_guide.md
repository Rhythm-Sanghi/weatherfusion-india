# WeatherFusion India demo guide

Before the demo: run `docker compose up -d db`, `backend\.venv\Scripts\python.exe -m alembic upgrade head`, `backend\.venv\Scripts\python.exe scripts\reset_demo.py`, start FastAPI with `uvicorn app.main:app --reload` from `backend`, and start the frontend with `pnpm dev` from `frontend`.

In a 3–5 minute flow, open Situation, Map, Events, and one event detail. Open Review Queue, select a NEEDS REVIEW event, enter a reason, make a human decision, and show the audit timeline. Then open Analytics to show persisted event and review counts, Sources for configured-source visibility, and System for component status. System assessment is evidence; human decisions remain separate.
