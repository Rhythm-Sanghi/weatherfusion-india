from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_geospatial_provider
from app.db import get_db_session
from app.domain.events import EventCategory, ProcessingStatus, SystemAssessment
from app.domain.providers import (
    ClusterQuery,
    GeographicAggregationFilters,
    GeospatialProvider,
    HotspotQuery,
    RegionalGroupingMethod,
)
from app.domain.reviews import AdminStatus
from app.schemas.geospatial import (
    BoundaryRegionalSummaryResponse,
    ClusterResponse,
    HotspotResponse,
    RegionalSummaryResponse,
)

router = APIRouter(prefix="/geo", tags=["geospatial"])
GeospatialProviderDep = Annotated[GeospatialProvider, Depends(get_geospatial_provider)]
SessionDep = Annotated[Session, Depends(get_db_session)]


def filters(
    event_type: EventCategory | None,
    severity: str | None,
    processing_status: ProcessingStatus | None,
    system_assessment: SystemAssessment | None,
    admin_status: AdminStatus | None,
    source_type: str | None,
    state: str | None,
    district: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    hours: int | None,
) -> GeographicAggregationFilters:
    observed_after = date_from
    if hours is not None and observed_after is None:
        observed_after = datetime.now(UTC) - timedelta(hours=hours)
    return GeographicAggregationFilters(
        event_type=event_type,
        severity=severity,
        processing_status=processing_status,
        system_assessment=system_assessment,
        admin_status=admin_status,
        source_type=source_type,
        state=state,
        district=district,
        observed_after=observed_after,
        observed_before=date_to,
    )


@router.get("/clusters", response_model=list[ClusterResponse])
async def clusters(
    geospatial_provider: GeospatialProviderDep,
    distance_meters: float = Query(default=20_000, gt=0, le=100_000),
    min_points: int = Query(default=2, ge=2, le=50),
    limit: int = Query(default=100, ge=1, le=200),
    event_type: EventCategory | None = None,
    severity: str | None = None,
    processing_status: ProcessingStatus | None = None,
    system_assessment: SystemAssessment | None = None,
    admin_status: AdminStatus | None = None,
    source_type: str | None = None,
    state: str | None = None,
    district: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    hours: int | None = Query(default=None, ge=1, le=24),
) -> list[ClusterResponse]:
    try:
        return await geospatial_provider.clusters(
            ClusterQuery(
                filters(
                    event_type, severity, processing_status, system_assessment,
                    admin_status, source_type, state, district, date_from, date_to, hours,
                ),
                distance_meters,
                min_points,
                limit,
            )
        )
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Geospatial provider is unavailable.") from exc


@router.get("/hotspots", response_model=list[HotspotResponse])
async def hotspots(
    geospatial_provider: GeospatialProviderDep,
    cell_size_meters: float = Query(default=25_000, ge=5_000, le=100_000),
    limit: int = Query(default=200, ge=1, le=500),
    event_type: EventCategory | None = None,
    severity: str | None = None,
    processing_status: ProcessingStatus | None = None,
    system_assessment: SystemAssessment | None = None,
    admin_status: AdminStatus | None = None,
    source_type: str | None = None,
    state: str | None = None,
    district: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    hours: int | None = Query(default=24, ge=1, le=24),
) -> list[HotspotResponse]:
    try:
        return await geospatial_provider.hotspots(
            HotspotQuery(
                filters(
                    event_type, severity, processing_status, system_assessment,
                    admin_status, source_type, state, district, date_from, date_to, hours,
                ),
                cell_size_meters,
                limit,
            )
        )
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Geospatial provider is unavailable.") from exc


@router.get(
    "/regions/summary",
    response_model=list[RegionalSummaryResponse] | BoundaryRegionalSummaryResponse,
)
async def regional_summary(
    geospatial_provider: GeospatialProviderDep,
    event_type: EventCategory | None = None,
    severity: str | None = None,
    processing_status: ProcessingStatus | None = None,
    system_assessment: SystemAssessment | None = None,
    admin_status: AdminStatus | None = None,
    source_type: str | None = None,
    state: str | None = None,
    district: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    hours: int | None = Query(default=None, ge=1, le=24),
    grouping_method: RegionalGroupingMethod = RegionalGroupingMethod.SOURCE_PROVIDED_LOCATION,
    administrative_level: str = Query(default="ADM1", pattern="^ADM[12]$"),
) -> list[RegionalSummaryResponse] | BoundaryRegionalSummaryResponse:
    summary_filters = filters(
        event_type, severity, processing_status, system_assessment,
        admin_status, source_type, state, district, date_from, date_to, hours,
    )
    if summary_filters.observed_after and summary_filters.observed_before and (
        summary_filters.observed_after > summary_filters.observed_before
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "date_from must not exceed date_to.")
    try:
        if grouping_method is RegionalGroupingMethod.BOUNDARY_DERIVED_LOCATION:
            return await geospatial_provider.boundary_regional_summary(
                summary_filters, administrative_level
            )
        return await geospatial_provider.regional_summary(
            summary_filters
        )
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Geospatial provider is unavailable.") from exc


@router.get("/boundaries")
def boundaries(
    session: SessionDep,
    level: str = Query(default="ADM1", pattern="^ADM[12]$"),
    boundary_id: str | None = None,
    geometry_purpose: str = Query(default="authoritative", pattern="^(authoritative|display)$"),
    limit: int = Query(default=36, ge=1, le=100),
) -> dict[str, object]:
    rows = session.execute(
        text(
            """SELECT b.id AS boundary_uuid,b.source_feature_id,b.name,b.source_code,d.boundary_id,d.year_represented,
                      d.license,d.attribution,ST_AsGeoJSON(CASE WHEN :geometry_purpose = 'display'
                      THEN CASE WHEN ST_IsValid(display_geometry.geometry) AND NOT ST_IsEmpty(display_geometry.geometry)
                          THEN display_geometry.geometry
                          ELSE b.geometry END
                      ELSE b.geometry END)::jsonb geometry
               FROM administrative_boundaries b JOIN boundary_datasets d ON d.id=b.dataset_id
               CROSS JOIN LATERAL (SELECT ST_Multi(ST_Transform(ST_SimplifyPreserveTopology(
                   ST_Transform(b.geometry, 6933), 1000), 4326)) AS geometry) display_geometry
               WHERE b.administrative_level=:level AND (CAST(:boundary_id AS text) IS NULL OR b.source_feature_id=:boundary_id)
               ORDER BY b.name LIMIT :limit"""
        ), {"level": level, "boundary_id": boundary_id, "geometry_purpose": geometry_purpose, "limit": limit},
    ).mappings().all()
    return {"type":"FeatureCollection","features":[{"type":"Feature","geometry":r["geometry"],"properties":{"id":r["source_feature_id"],"boundary_uuid":str(r["boundary_uuid"]),"name":r["name"],"source_code":r["source_code"],"dataset_id":r["boundary_id"],"vintage":r["year_represented"],"license":r["license"],"attribution":r["attribution"],"level":level}} for r in rows]}


@router.get("/events/{event_id}/boundaries")
def event_boundaries(event_id: str, session: SessionDep) -> dict[str, object]:
    event = session.execute(text("SELECT id,location FROM weather_events WHERE id=CAST(:id AS uuid)"), {"id":event_id}).mappings().one_or_none()
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found.")
    result: dict[str, object] = {"method":"ST_Covers independent ADM1/ADM2", "source_location":"SOURCE_PROVIDED_LOCATION", "boundary_location":"BOUNDARY_DERIVED_LOCATION", "levels":{}}
    for level in ("ADM1", "ADM2"):
        if event["location"] is None:
            result["levels"][level] = {"status": "NO_COORDINATES", "candidates": []}
            continue
        rows=session.execute(text("""SELECT b.source_feature_id,b.name,b.source_code,d.boundary_id,d.year_represented
          FROM administrative_boundaries b JOIN boundary_datasets d ON d.id=b.dataset_id
          WHERE b.administrative_level=:level AND ST_Covers(b.geometry,(SELECT location::geometry FROM weather_events WHERE id=CAST(:id AS uuid)))"""),{"level":level,"id":event_id}).mappings().all()
        result["levels"][level]={"status":"UNMATCHED" if not rows else "MATCHED" if len(rows)==1 else "AMBIGUOUS","candidates":[dict(r) for r in rows]}
    result["cross_vintage_note"]="ADM1 2011 and ADM2 2021 are independent; Lakshadweep alignment is limited."
    return result
