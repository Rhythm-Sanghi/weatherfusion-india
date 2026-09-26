import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.dependencies import get_geospatial_provider, get_verification_provider
from app.core.config import get_settings
from app.db import get_db_session
from app.domain.events import ProcessingStatus, SystemAssessment
from app.domain.providers import GeospatialProvider, VerificationProvider
from app.domain.reviews import AdminStatus
from app.integrations.social.controlled_feed import CONTROLLED_POSTS, SocialWeatherConnector
from app.integrations.weather.open_meteo import OpenMeteoConnector
from app.models.event import Source, WeatherEvent
from app.schemas.events import EventCreate
from app.services.ingestion import DuplicateExternalIdError, IngestionService
from app.services.media import attach_media_evidence

router = APIRouter(tags=["operations"])
logger = logging.getLogger("weatherfusion.operations")
SessionDep = Annotated[Session, Depends(get_db_session)]
VerificationDep = Annotated[VerificationProvider, Depends(get_verification_provider)]
GeospatialDep = Annotated[GeospatialProvider, Depends(get_geospatial_provider)]

DEMO_SCENARIOS = {
    "mumbai-flood": {"name": "Mumbai flood response", "post_ids": {"SOCIAL-001", "SOCIAL-002"}},
    "guwahati-storm": {"name": "Guwahati thunderstorm response", "post_ids": {"SOCIAL-003"}},
    "rajasthan-dust": {"name": "Rajasthan dust-storm response", "post_ids": {"SOCIAL-006", "SOCIAL-014"}},
}


def counts(session: Session, column: object) -> dict[str, int]:
    return {str(key): value for key, value in session.execute(select(column, func.count()).group_by(column)).all()}


@router.get("/analytics/overview")
def analytics_overview(session: SessionDep) -> dict[str, int]:
    total = session.scalar(select(func.count()).select_from(WeatherEvent)) or 0
    admin, assessment, processing = counts(session, WeatherEvent.admin_status), counts(session, WeatherEvent.system_assessment), counts(session, WeatherEvent.processing_status)
    return {"total_events": total, "unreviewed_events": admin.get(str(AdminStatus.UNREVIEWED), 0), "verified_events": admin.get(str(AdminStatus.VERIFIED), 0), "rejected_events": admin.get(str(AdminStatus.REJECTED), 0), "escalated_events": admin.get(str(AdminStatus.ESCALATED), 0), "needs_review": assessment.get(str(SystemAssessment.NEEDS_REVIEW), 0), "disputed": assessment.get(str(SystemAssessment.DISPUTED), 0), "partial_processing": processing.get(str(ProcessingStatus.PARTIAL), 0)}


@router.get("/analytics/distribution")
def analytics_distribution(session: SessionDep) -> dict[str, dict[str, int]]:
    return {"event_type": counts(session, WeatherEvent.event_type), "severity": counts(session, WeatherEvent.severity), "state": counts(session, WeatherEvent.state), "system_assessment": counts(session, WeatherEvent.system_assessment), "admin_status": counts(session, WeatherEvent.admin_status)}


@router.get("/analytics/trends")
def analytics_trends(session: SessionDep) -> dict[str, list[dict[str, object]]]:
    rows = session.execute(select(func.date(WeatherEvent.observed_at), func.count()).group_by(func.date(WeatherEvent.observed_at)).order_by(func.date(WeatherEvent.observed_at))).all()
    return {"bucket": "daily observed_at", "items": [{"date": str(day), "count": count} for day, count in rows]}


@router.get("/sources")
def sources(session: SessionDep) -> list[dict[str, object]]:
    rows = session.execute(select(Source, func.count(WeatherEvent.id), func.max(WeatherEvent.received_at)).outerjoin(WeatherEvent).group_by(Source.id)).all()
    result = [{"id": str(source.id), "name": source.name, "source_type": source.source_type, "enabled": source.enabled, "event_count": count, "last_activity": last.isoformat() if last else None, "status": "demo fixture" if source.source_type == "DEMO" else ("controlled dataset" if source.source_type == "SOCIAL_PROTOTYPE" else ("configured" if source.enabled else "disabled")), "mode": "controlled" if source.source_type == "SOCIAL_PROTOTYPE" else None, "records_available": len(CONTROLLED_POSTS) if source.source_type == "SOCIAL_PROTOTYPE" else None} for source, count, last in rows]
    if not any(item["source_type"] == "SOCIAL_PROTOTYPE" for item in result):
        result.append({"id": "controlled-social-feed", "name": "Controlled Social Weather Feed", "source_type": "SOCIAL_PROTOTYPE", "enabled": True, "event_count": 0, "last_activity": None, "status": "controlled dataset", "mode": "controlled", "records_available": len(CONTROLLED_POSTS)})
    return result


@router.get("/system/status")
def system_status(session: SessionDep) -> dict[str, object]:
    try:
        session.execute(text("SELECT 1"))
        database = {"status": "operational"}
    except Exception:
        database = {"status": "unavailable"}
    settings = get_settings()
    geospatial = {
        "status": "mock" if settings.geospatial_provider == "mock" else "available",
        "adapter": "connected",
        "implementation": settings.geospatial_provider,
    }
    if settings.geospatial_provider == "postgis":
        try:
            geospatial["postgis_version"] = session.scalar(text("SELECT PostGIS_Version()"))
        except Exception:
            geospatial["status"] = "unavailable"
            geospatial["adapter"] = "unavailable"
    return {"api": {"status": "operational"}, "database": database, "verification_provider": {"status": "available", "adapter": "connected", "implementation": settings.verification_provider}, "geospatial_provider": geospatial}


@router.get("/weather/forecast")
async def weather_forecast() -> dict[str, object]:
    settings = get_settings()
    if settings.demo_mode:
        return {"status": "demo_offline", "source": "open-meteo", "forecast": None, "detail": "DEMO_MODE prevents live external calls; use controlled records and cached weather context."}
    if not settings.weather_connector_enabled:
        return {"status": "disabled", "source": "open-meteo", "forecast": None}
    try:
        result = await OpenMeteoConnector(settings).fetch_forecast()
    except RuntimeError as exc:
        return {"status": "unavailable", "source": "open-meteo", "forecast": None, "detail": str(exc)}
    cache_age_seconds = max(0, round((datetime.now(UTC) - result.fetched_at).total_seconds())) if result.mode == "cached" else 0
    return {
        "status": result.mode,
        "source": "open-meteo",
        "location": {"name": settings.weather_default_location_name, "latitude": settings.weather_default_latitude, "longitude": settings.weather_default_longitude},
        "observation_time": result.payload.get("current", {}).get("time"),
        "retrieved_at": result.fetched_at.isoformat(),
        "cache_age_seconds": cache_age_seconds,
        "forecast": result.payload,
        "disclaimer": "Forecast context only. It is not a verified ground-level incident observation.",
    }


@router.post("/ingestion/weather")
async def ingest_external_weather(session: SessionDep, verification: VerificationDep, geospatial: GeospatialDep) -> dict[str, object]:
    settings = get_settings()
    if settings.demo_mode:
        return {"source": "open-meteo", "received": 0, "created": 0, "duplicates": 0, "failed": 0, "mode": "demo_offline"}
    if not settings.weather_connector_enabled:
        return {"source": "open-meteo", "received": 0, "created": 0, "duplicates": 0, "failed": 0, "mode": "disabled"}
    try:
        fetched = await OpenMeteoConnector(settings).fetch()
    except RuntimeError as exc:
        return {"source": "open-meteo", "received": 0, "created": 0, "duplicates": 0, "failed": 1, "mode": "unavailable", "detail": str(exc)}
    created = duplicates = failed = 0
    service = IngestionService(session, verification, geospatial)
    for raw in fetched.records:
        try:
            payload = EventCreate.model_validate(
                OpenMeteoConnector.normalize(raw, fetched.mode, fetched.fetched_at)
            )
            await service.ingest(payload, raw["payload"])
            created += 1
        except DuplicateExternalIdError:
            duplicates += 1
        except Exception as exc:
            logger.warning(
                "weather ingestion item failed",
                extra={"source": "open_meteo", "error_type": type(exc).__name__},
            )
            failed += 1
    return {"source": "open-meteo", "received": len(fetched.records), "created": created, "duplicates": duplicates, "failed": failed, "mode": fetched.mode}


@router.post("/ingestion/social")
async def ingest_controlled_social_feed(session: SessionDep, verification: VerificationDep, geospatial: GeospatialDep) -> dict[str, object]:
    posts = await SocialWeatherConnector().fetch_posts()
    matched = [post for post in posts if SocialWeatherConnector.matches_weather_hashtag(post)]
    created = duplicates = failed = 0
    service = IngestionService(session, verification, geospatial)
    for post in matched:
        try:
            event = await service.ingest(EventCreate.model_validate(SocialWeatherConnector.normalize(post)), post)
            if post["media"]:
                attach_media_evidence(session, event, post["media"], source_name="Controlled Social Weather Feed", is_demo=True)
            created += 1
        except DuplicateExternalIdError:
            duplicates += 1
        except Exception as exc:
            logger.warning(
                "social ingestion item failed",
                extra={
                    "source": "controlled_social_feed",
                    "post_id": post.get("post_id"),
                    "error_type": type(exc).__name__,
                },
            )
            failed += 1
    return {"source": "controlled_social_feed", "received": len(posts), "matched": len(matched), "created": created, "duplicates": duplicates, "failed": failed, "mode": "controlled"}


@router.get("/demo/feed")
async def controlled_demo_feed() -> dict[str, object]:
    """Expose only clearly-labelled fixture posts for the live-feed demo screen."""
    posts = await SocialWeatherConnector().fetch_posts()
    matched = [post for post in posts if SocialWeatherConnector.matches_weather_hashtag(post)]
    return {"mode": "controlled_demo", "disclaimer": "Controlled prototype data, not a live social-media connection.", "items": matched}


@router.get("/demo/scenarios")
def demo_scenarios() -> list[dict[str, object]]:
    return [{"id": key, "name": value["name"], "post_count": len(value["post_ids"])} for key, value in DEMO_SCENARIOS.items()]


@router.post("/demo/scenarios/{scenario_id}")
async def activate_demo_scenario(
    scenario_id: str, session: SessionDep, verification: VerificationDep, geospatial: GeospatialDep
) -> dict[str, object]:
    scenario = DEMO_SCENARIOS.get(scenario_id)
    if scenario is None:
        return {"status": "unknown_scenario", "scenario_id": scenario_id}
    posts = await SocialWeatherConnector().fetch_posts()
    selected = [post for post in posts if post["post_id"] in scenario["post_ids"]]
    service = IngestionService(session, verification, geospatial)
    created = duplicates = failed = 0
    for post in selected:
        payload = SocialWeatherConnector.normalize(post)
        payload["external_id"] = f"scenario:{scenario_id}:{post['post_id']}"
        payload["metadata"] = {**payload["metadata"], "demo_scenario": scenario_id}
        try:
            event = await service.ingest(EventCreate.model_validate(payload), post)
            if post["media"]:
                attach_media_evidence(session, event, post["media"], source_name="Controlled Social Weather Feed", is_demo=True)
            created += 1
        except DuplicateExternalIdError:
            duplicates += 1
        except Exception as exc:
            logger.warning(
                "scenario ingestion item failed",
                extra={
                    "source": "controlled_social_feed",
                    "scenario_id": scenario_id,
                    "post_id": post.get("post_id"),
                    "error_type": type(exc).__name__,
                },
            )
            failed += 1
    return {"status": "activated", "mode": "controlled_demo", "scenario_id": scenario_id, "scenario_name": scenario["name"], "created": created, "duplicates": duplicates, "failed": failed}
