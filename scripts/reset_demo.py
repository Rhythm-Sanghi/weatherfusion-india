"""Delete only marked demo fixtures, then restore the deterministic seed."""
import runpy
import sys
from importlib import import_module
from pathlib import Path

from sqlalchemy import delete

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
SessionLocal = import_module("app.db").SessionLocal
WeatherEvent = import_module("app.models.event").WeatherEvent

with SessionLocal.begin() as session:
    session.execute(delete(WeatherEvent).where(WeatherEvent.metadata_["demo_fixture"].as_boolean() == True))
runpy.run_path(str(Path(__file__).with_name("seed_phase3_demo.py")), run_name="__main__")
