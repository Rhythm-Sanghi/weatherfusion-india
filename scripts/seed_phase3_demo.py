"""Create or update the deterministic, display-only Phase 3 demo event set."""
import sys
from datetime import UTC, datetime, timedelta
from importlib import import_module
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

SessionLocal = import_module("app.db").SessionLocal
events = import_module("app.domain.events")
reviews = import_module("app.domain.reviews")
models = import_module("app.models.event")
EventCategory = events.EventCategory
ProcessingStatus = events.ProcessingStatus
SystemAssessment = events.SystemAssessment
AdminStatus = reviews.AdminStatus
RawIngestRecord = models.RawIngestRecord
Source = models.Source
WeatherEvent = models.WeatherEvent


BASE_TIME = datetime(2026, 9, 19, 6, tzinfo=UTC)
FIXTURES = [
    ("demo-001", EventCategory.FLOOD, "CRITICAL", "Urban flooding reported in Guwahati", "Assam", "Kamrup Metropolitan", "Guwahati", 26.1445, 91.7362, ProcessingStatus.COMPLETE, SystemAssessment.NEEDS_REVIEW, AdminStatus.ESCALATED),
    ("demo-002", EventCategory.HEAVY_RAINFALL, "HIGH", "Heavy rainfall reported in Mumbai", "Maharashtra", "Mumbai Suburban", "Mumbai", 19.0760, 72.8777, ProcessingStatus.COMPLETE, SystemAssessment.CORROBORATED, AdminStatus.VERIFIED),
    ("demo-003", EventCategory.HEATWAVE, "HIGH", "Heatwave conditions reported in Jaipur", "Rajasthan", "Jaipur", "Jaipur", 26.9124, 75.7873, ProcessingStatus.PARTIAL, SystemAssessment.UNAVAILABLE, AdminStatus.UNREVIEWED),
    ("demo-004", EventCategory.THUNDERSTORM, "MODERATE", "Thunderstorm reported near Kolkata", "West Bengal", "Kolkata", "Kolkata", 22.5726, 88.3639, ProcessingStatus.COMPLETE, SystemAssessment.PENDING, AdminStatus.UNREVIEWED),
    ("demo-005", EventCategory.FOG, "MODERATE", "Dense fog reported in Lucknow", "Uttar Pradesh", "Lucknow", "Lucknow", 26.8467, 80.9462, ProcessingStatus.COMPLETE, SystemAssessment.NEEDS_REVIEW, AdminStatus.ESCALATED),
    ("demo-006", EventCategory.STRONG_WIND, "HIGH", "Strong winds reported in Chennai", "Tamil Nadu", "Chennai", "Chennai", 13.0827, 80.2707, ProcessingStatus.COMPLETE, SystemAssessment.CORROBORATED, AdminStatus.VERIFIED),
    ("demo-007", EventCategory.DUST_STORM, "MODERATE", "Dust storm reported in Jodhpur", "Rajasthan", "Jodhpur", "Jodhpur", 26.2389, 73.0243, ProcessingStatus.PARTIAL, SystemAssessment.UNAVAILABLE, AdminStatus.UNREVIEWED),
    ("demo-008", EventCategory.HEAVY_RAINFALL, "HIGH", "Intense rainfall reported in Kochi", "Kerala", "Ernakulam", "Kochi", 9.9312, 76.2673, ProcessingStatus.COMPLETE, SystemAssessment.DISPUTED, AdminStatus.UNREVIEWED),
    ("demo-009", EventCategory.FLOOD, "HIGH", "River flooding reported in Patna", "Bihar", "Patna", "Patna", 25.5941, 85.1376, ProcessingStatus.COMPLETE, SystemAssessment.CORROBORATED, AdminStatus.VERIFIED),
    ("demo-010", EventCategory.THUNDERSTORM, "LOW", "Thunderstorm reported in Bengaluru", "Karnataka", "Bengaluru Urban", "Bengaluru", 12.9716, 77.5946, ProcessingStatus.COMPLETE, SystemAssessment.PENDING, AdminStatus.UNREVIEWED),
    ("demo-011", EventCategory.STRONG_WIND, "MODERATE", "Wind advisory reported in Bhubaneswar", "Odisha", "Khordha", "Bhubaneswar", 20.2961, 85.8245, ProcessingStatus.FAILED, SystemAssessment.UNAVAILABLE, AdminStatus.ESCALATED),
    ("demo-012", EventCategory.HEATWAVE, "CRITICAL", "Extreme heat reported in Nagpur", "Maharashtra", "Nagpur", "Nagpur", 21.1458, 79.0882, ProcessingStatus.COMPLETE, SystemAssessment.NEEDS_REVIEW, AdminStatus.UNREVIEWED),
]


def main() -> None:
    with SessionLocal.begin() as session:
        source = session.scalar(select(Source).where(Source.name == "Phase 3 Demo Fixtures"))
        if source is None:
            source = Source(name="Phase 3 Demo Fixtures", source_type="DEMO", reliability=None)
            session.add(source)
            session.flush()

        for index, fixture in enumerate(FIXTURES):
            external_id, category, severity, title, state, district, city, latitude, longitude, processing, assessment, admin = fixture
            event = session.scalar(select(WeatherEvent).where(WeatherEvent.source_id == source.id, WeatherEvent.external_id == external_id))
            values = {"event_type": category, "severity": severity, "title": title, "description": f"Deterministic demo fixture: {title.lower()}.", "raw_text": title, "latitude": latitude, "longitude": longitude, "state": state, "district": district, "city": city, "observed_at": BASE_TIME - timedelta(hours=index), "processing_status": processing, "system_assessment": assessment, "admin_status": admin, "metadata_": {"demo_fixture": True, "status_origin": "curated display fixture; not provider output"}}
            if event is None:
                event = WeatherEvent(source_id=source.id, external_id=external_id, **values)
                session.add(event)
                session.add(RawIngestRecord(source_id=source.id, external_id=external_id, raw_payload={"demo_fixture": True, "title": title}))
            else:
                for key, value in values.items():
                    setattr(event, key, value)
    print(f"Seeded {len(FIXTURES)} deterministic Phase 3 demo events.")


if __name__ == "__main__":
    main()
