from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ClusterResponse(BaseModel):
    cluster_id: str
    event_ids: list[str]
    event_count: int
    longitude: float
    latitude: float
    event_type_distribution: dict[str, int]
    severity_distribution: dict[str, int]
    system_assessment_distribution: dict[str, int]
    admin_status_distribution: dict[str, int]
    observed_from: datetime
    observed_to: datetime
    method: str


class HotspotResponse(BaseModel):
    cell_id: str
    event_count: int
    event_ids: list[str]
    longitude: float
    latitude: float
    event_type_distribution: dict[str, int]
    severity_distribution: dict[str, int]
    geometry: dict[str, Any]
    method: str


class RegionalSummaryResponse(BaseModel):
    state: str
    district: str
    event_count: int
    grouping_method: str


class BoundaryRegionalRowResponse(BaseModel):
    boundary_id: str
    administrative_name: str
    source_administrative_code: str | None = None
    dataset_identifier: str
    dataset_administrative_vintage: int | None = None
    event_count: int
    event_type_distribution: dict[str, int]
    system_assessment_distribution: dict[str, int]
    admin_status_distribution: dict[str, int]


class BoundaryRegionalSummaryResponse(BaseModel):
    administrative_level: str
    grouping_method: str
    regions: list[BoundaryRegionalRowResponse]
    categories: dict[str, int]
    filtered_event_count: int
    applied_observation_time_range: dict[str, datetime | None]
    coverage_note: str


class BoundaryStatusResponse(BaseModel):
    available: bool
    status: str
    detail: str
    dataset: dict[str, Any] | None = None
