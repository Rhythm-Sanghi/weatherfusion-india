from datetime import UTC, datetime

from sqlalchemy import String, cast, func, select, text
from sqlalchemy.orm import Session

from app.domain.providers import (
    ClusterQuery,
    GeographicAggregationFilters,
    GeospatialEventInput,
    HotspotQuery,
    LocationEnrichment,
    MapEventFilters,
    NearbyEvent,
    NearbyQuery,
    ProviderMetadata,
    RegionSummary,
    RegionSummaryFilters,
)
from app.models.event import Source, WeatherEvent


class PostgisGeospatialProvider:
    """Request-session PostGIS adapter; it never owns transaction lifecycle."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _metadata() -> ProviderMetadata:
        return ProviderMetadata("postgis", "3.4", datetime.now(UTC))

    @staticmethod
    def _aggregation_conditions(
        filters: GeographicAggregationFilters,
        *,
        require_location: bool = True,
    ) -> tuple[list[str], dict[str, object]]:
        conditions = ["e.location IS NOT NULL"] if require_location else []
        params: dict[str, object] = {}
        for column, value in (
            ("e.event_type", filters.event_type),
            ("e.severity", filters.severity),
            ("e.processing_status", filters.processing_status),
            ("e.system_assessment", filters.system_assessment),
            ("e.admin_status", filters.admin_status),
            ("s.source_type", filters.source_type),
            ("e.state", filters.state),
            ("e.district", filters.district),
        ):
            if value is not None:
                key = column.replace(".", "_")
                conditions.append(f"{column} = :{key}")
                params[key] = getattr(value, "value", value)
        if filters.observed_after is not None:
            conditions.append("e.observed_at >= :observed_after")
            params["observed_after"] = filters.observed_after
        if filters.observed_before is not None:
            conditions.append("e.observed_at <= :observed_before")
            params["observed_before"] = filters.observed_before
        return conditions, params

    async def enrich_location(self, event: GeospatialEventInput) -> LocationEnrichment:
        ready = self.session.scalar(
            select(WeatherEvent.location).where(WeatherEvent.id == event.event_id)
        )
        return LocationEnrichment(
            event.state,
            event.district,
            event.city,
            "SPATIAL_READY" if ready is not None else "NO_COORDINATES",
            self._metadata(),
        )

    async def find_nearby(
        self, event: GeospatialEventInput, query: NearbyQuery
    ) -> list[NearbyEvent]:
        source_location = (
            select(WeatherEvent.location)
            .where(WeatherEvent.id == event.event_id)
            .scalar_subquery()
        )
        distance = func.ST_Distance(WeatherEvent.location, source_location).label(
            "distance_meters"
        )
        statement = (
            select(WeatherEvent, Source.name, distance)
            .join(Source, WeatherEvent.source_id == Source.id)
            .where(
                WeatherEvent.id != event.event_id,
                WeatherEvent.location.is_not(None),
                func.ST_DWithin(WeatherEvent.location, source_location, query.radius_meters),
            )
        )
        if query.observed_after is not None:
            statement = statement.where(WeatherEvent.observed_at >= query.observed_after)
        if query.observed_before is not None:
            statement = statement.where(WeatherEvent.observed_at <= query.observed_before)
        for column, value in (
            (WeatherEvent.event_type, query.event_type),
            (WeatherEvent.severity, query.severity),
            (WeatherEvent.processing_status, query.processing_status),
            (WeatherEvent.system_assessment, query.system_assessment),
            (WeatherEvent.admin_status, query.admin_status),
            (Source.source_type, query.source_type),
        ):
            if value is not None:
                statement = statement.where(column == value)
        rows = self.session.execute(
            statement.order_by(distance, cast(WeatherEvent.id, String)).limit(query.limit)
        ).all()
        return [
            NearbyEvent(
                event_id=item.id,
                relationship="NEARBY_SPATIAL_EVIDENCE",
                distance_meters=float(distance_meters),
                observed_at=item.observed_at,
                title=item.title,
                event_type=item.event_type,
                source_name=source_name,
                metadata=self._metadata(),
            )
            for item, source_name, distance_meters in rows
        ]

    async def region_summary(self, filters: RegionSummaryFilters) -> list[RegionSummary]:
        statement = select(WeatherEvent.state, func.count()).where(
            WeatherEvent.location.is_not(None)
        )
        if filters.state:
            statement = statement.where(WeatherEvent.state == filters.state)
        if filters.event_type:
            statement = statement.where(WeatherEvent.event_type == filters.event_type)
        if filters.observed_after:
            statement = statement.where(WeatherEvent.observed_at >= filters.observed_after)
        return [
            RegionSummary(
                str(state or "unassigned"),
                str(state or "Unassigned"),
                count,
                self._metadata(),
            )
            for state, count in self.session.execute(
                statement.group_by(WeatherEvent.state)
            ).all()
        ]

    async def geojson_features(
        self, filters: MapEventFilters
    ) -> list[dict[str, object]]:
        statement = (
            select(WeatherEvent, Source.name, Source.source_type)
            .join(Source)
            .where(WeatherEvent.location.is_not(None))
        )
        for column, value in (
            (WeatherEvent.event_type, filters.event_type),
            (WeatherEvent.severity, filters.severity),
            (WeatherEvent.processing_status, filters.processing_status),
            (WeatherEvent.system_assessment, filters.system_assessment),
            (WeatherEvent.admin_status, filters.admin_status),
        ):
            if value is not None:
                statement = statement.where(column == value)
        if filters.observed_after is not None:
            statement = statement.where(WeatherEvent.observed_at >= filters.observed_after)
        if filters.observed_before is not None:
            statement = statement.where(WeatherEvent.observed_at <= filters.observed_before)
        if filters.boundary_id is not None:
            statement = statement.where(
                text(
                    """EXISTS (SELECT 1 FROM administrative_boundaries ab
                    WHERE ab.id = CAST(:boundary_id AS uuid)
                    AND ST_Covers(ab.geometry, weather_events.location::geometry))"""
                ).bindparams(boundary_id=str(filters.boundary_id))
            )
        return [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [event.longitude, event.latitude],
                },
                "properties": {
                    "id": str(event.id),
                    "event_type": event.event_type.value,
                    "severity": event.severity,
                    "processing_status": event.processing_status.value,
                    "system_assessment": event.system_assessment.value,
                    "admin_status": event.admin_status.value,
                    "observed_at": event.observed_at.isoformat(),
                    "source_name": name,
                    "source_type": source_type,
                    "origin_mode": event.metadata_.get("origin_mode"),
                },
            }
            for event, name, source_type in self.session.execute(
                statement.order_by(
                    WeatherEvent.observed_at.desc(), cast(WeatherEvent.id, String)
                ).limit(filters.limit)
            ).all()
        ]

    async def clusters(self, query: ClusterQuery) -> list[dict[str, object]]:
        conditions, params = self._aggregation_conditions(query.filters)
        params.update(
            distance_meters=query.distance_meters,
            min_points=query.min_points,
        )
        rows = self.session.execute(
            text(
                f"""
                WITH filtered AS (
                    SELECT e.id, e.event_type, e.severity, e.observed_at,
                           e.system_assessment, e.admin_status,
                           ST_Transform(e.location::geometry, 6933) AS projected
                    FROM weather_events e JOIN sources s ON s.id = e.source_id
                    WHERE {' AND '.join(conditions)}
                ), clustered AS (
                    SELECT *, ST_ClusterDBSCAN(
                        projected, eps := :distance_meters, minpoints := :min_points
                    ) OVER () AS cluster_number
                    FROM filtered
                )
                SELECT id, event_type, severity, observed_at, system_assessment, admin_status,
                       cluster_number,
                       ST_X(ST_Transform(projected, 4326)) AS longitude,
                       ST_Y(ST_Transform(projected, 4326)) AS latitude
                FROM clustered WHERE cluster_number IS NOT NULL
                ORDER BY cluster_number, id::text
                """
            ),
            params,
        ).mappings().all()
        grouped: dict[int, list[dict[str, object]]] = {}
        for row in rows:
            grouped.setdefault(int(row["cluster_number"]), []).append(dict(row))
        output: list[dict[str, object]] = []
        for index, members in enumerate(
            sorted(grouped.values(), key=lambda items: str(items[0]["id"])), start=1
        ):
            types: dict[str, int] = {}
            severity: dict[str, int] = {}
            assessments: dict[str, int] = {}
            reviews: dict[str, int] = {}
            for member in members:
                for bucket, value in (
                    (types, member["event_type"]),
                    (severity, member["severity"]),
                    (assessments, member["system_assessment"]),
                    (reviews, member["admin_status"]),
                ):
                    label = str(value)
                    bucket[label] = bucket.get(label, 0) + 1
            output.append(
                {
                    "cluster_id": f"query-cluster-{index}",
                    "event_ids": [str(member["id"]) for member in members],
                    "event_count": len(members),
                    "longitude": sum(float(member["longitude"]) for member in members)
                    / len(members),
                    "latitude": sum(float(member["latitude"]) for member in members)
                    / len(members),
                    "event_type_distribution": types,
                    "severity_distribution": severity,
                    "system_assessment_distribution": assessments,
                    "admin_status_distribution": reviews,
                    "observed_from": min(member["observed_at"] for member in members),
                    "observed_to": max(member["observed_at"] for member in members),
                    "method": "ST_ClusterDBSCAN EPSG:6933 projected metres",
                }
            )
        return output[: query.limit]

    async def hotspots(self, query: HotspotQuery) -> list[dict[str, object]]:
        conditions, params = self._aggregation_conditions(query.filters)
        params["cell_size_meters"] = query.cell_size_meters
        params["limit"] = query.limit
        rows = self.session.execute(
            text(
                f"""
                WITH filtered AS (
                    SELECT e.id, e.event_type, e.severity,
                           ST_Transform(e.location::geometry, 6933) AS projected
                    FROM weather_events e JOIN sources s ON s.id = e.source_id
                    WHERE {' AND '.join(conditions)}
                ), cells AS (
                    SELECT ST_SnapToGrid(projected, :cell_size_meters) AS cell,
                           id, event_type, severity FROM filtered
                )
                SELECT ST_X(cell) AS cell_x, ST_Y(cell) AS cell_y,
                       ST_X(ST_Transform(ST_Centroid(cell), 4326)) AS longitude,
                       ST_Y(ST_Transform(ST_Centroid(cell), 4326)) AS latitude,
                       ST_AsGeoJSON(ST_Transform(ST_Envelope(cell), 4326))::jsonb AS geometry,
                       count(*) AS event_count,
                       array_agg(id::text ORDER BY id::text) AS event_ids,
                       jsonb_object_agg(event_type, type_count) AS event_types,
                       jsonb_object_agg(severity, severity_count) AS severities
                FROM (
                    SELECT cell, id, event_type, severity,
                           count(*) OVER (PARTITION BY cell, event_type) AS type_count,
                           count(*) OVER (PARTITION BY cell, severity) AS severity_count
                    FROM cells
                ) aggregates
                GROUP BY cell
                ORDER BY event_count DESC, cell_x, cell_y
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
        return [
            {
                "cell_id": f"epsg6933-{query.cell_size_meters:g}-{row['cell_x']:g}-{row['cell_y']:g}",
                "event_count": row["event_count"],
                "event_ids": row["event_ids"],
                "longitude": float(row["longitude"]),
                "latitude": float(row["latitude"]),
                "event_type_distribution": row["event_types"],
                "severity_distribution": row["severities"],
                "geometry": row["geometry"],
                "method": "EPSG:6933 fixed metre grid",
            }
            for row in rows
        ]

    async def regional_summary(
        self, filters: GeographicAggregationFilters
    ) -> list[dict[str, object]]:
        conditions, params = self._aggregation_conditions(filters)
        rows = self.session.execute(
            text(
                f"""
                SELECT coalesce(e.state, 'Unknown') AS state,
                       coalesce(e.district, 'Unknown') AS district,
                       count(*) AS event_count
                FROM weather_events e JOIN sources s ON s.id = e.source_id
                WHERE {' AND '.join(conditions)}
                GROUP BY e.state, e.district
                ORDER BY event_count DESC, state, district
                """
            ),
            params,
        ).mappings().all()
        return [
            {
                "state": row["state"],
                "district": row["district"],
                "event_count": row["event_count"],
                "grouping_method": "source-provided administrative attributes",
            }
            for row in rows
        ]

    async def boundary_regional_summary(
        self, filters: GeographicAggregationFilters, administrative_level: str
    ) -> dict[str, object]:
        conditions, params = self._aggregation_conditions(filters, require_location=False)
        params["administrative_level"] = administrative_level
        result = self.session.scalar(
            text(
                f"""
                WITH filtered AS (
                    SELECT e.id, e.location, e.event_type, e.system_assessment, e.admin_status
                    FROM weather_events e JOIN sources s ON s.id = e.source_id
                    WHERE {' AND '.join(conditions) if conditions else 'TRUE'}
                ), matches AS (
                    SELECT f.*, count(b.id) AS match_count,
                           jsonb_agg(jsonb_build_object(
                               'boundary_id', b.id::text, 'name', b.name,
                               'source_code', b.source_code, 'dataset_identifier', d.boundary_id,
                               'vintage', d.year_represented
                           )) FILTER (WHERE b.id IS NOT NULL) AS boundary_matches
                    FROM filtered f
                    LEFT JOIN administrative_boundaries b
                      ON f.location IS NOT NULL
                     AND b.administrative_level = :administrative_level
                     AND ST_Covers(b.geometry, f.location::geometry)
                    LEFT JOIN boundary_datasets d ON d.id = b.dataset_id
                    GROUP BY f.id, f.location, f.event_type, f.system_assessment, f.admin_status
                ), classified AS (
                    SELECT *, CASE
                        WHEN location IS NULL THEN 'NO_COORDINATES'
                        WHEN match_count = 0 THEN 'UNMATCHED'
                        WHEN match_count = 1 THEN 'MATCHED'
                        ELSE 'AMBIGUOUS'
                    END AS match_status
                    FROM matches
                ), matched AS (
                    SELECT *, boundary_matches -> 0 AS boundary
                    FROM classified WHERE match_status = 'MATCHED'
                ), region_counts AS (
                    SELECT boundary ->> 'boundary_id' AS boundary_id,
                           boundary ->> 'name' AS administrative_name,
                           boundary ->> 'source_code' AS source_administrative_code,
                           boundary ->> 'dataset_identifier' AS dataset_identifier,
                           (boundary ->> 'vintage')::integer AS dataset_administrative_vintage,
                           count(*) AS event_count
                    FROM matched GROUP BY 1, 2, 3, 4, 5
                ), type_counts AS (
                    SELECT boundary ->> 'boundary_id' AS boundary_id, event_type, count(*) AS count
                    FROM matched GROUP BY 1, 2
                ), type_json AS (
                    SELECT boundary_id, jsonb_object_agg(event_type, count) AS distribution
                    FROM type_counts GROUP BY boundary_id
                ), assessment_counts AS (
                    SELECT boundary ->> 'boundary_id' AS boundary_id, system_assessment, count(*) AS count
                    FROM matched GROUP BY 1, 2
                ), assessment_json AS (
                    SELECT boundary_id, jsonb_object_agg(system_assessment, count) AS distribution
                    FROM assessment_counts GROUP BY boundary_id
                ), review_counts AS (
                    SELECT boundary ->> 'boundary_id' AS boundary_id, admin_status, count(*) AS count
                    FROM matched GROUP BY 1, 2
                ), review_json AS (
                    SELECT boundary_id, jsonb_object_agg(admin_status, count) AS distribution
                    FROM review_counts GROUP BY boundary_id
                ), category_counts AS (
                    SELECT match_status, count(*) AS count FROM classified
                    WHERE match_status <> 'MATCHED' GROUP BY match_status
                )
                SELECT jsonb_build_object(
                    'regions', coalesce((
                        SELECT jsonb_agg(jsonb_build_object(
                            'boundary_id', r.boundary_id,
                            'administrative_name', r.administrative_name,
                            'source_administrative_code', r.source_administrative_code,
                            'dataset_identifier', r.dataset_identifier,
                            'dataset_administrative_vintage', r.dataset_administrative_vintage,
                            'event_count', r.event_count,
                            'event_type_distribution', t.distribution,
                            'system_assessment_distribution', a.distribution,
                            'admin_status_distribution', h.distribution
                        ) ORDER BY r.administrative_name, r.boundary_id)
                        FROM region_counts r
                        JOIN type_json t USING (boundary_id)
                        JOIN assessment_json a USING (boundary_id)
                        JOIN review_json h USING (boundary_id)
                    ), '[]'::jsonb),
                    'categories', jsonb_build_object(
                        'AMBIGUOUS', coalesce((SELECT count FROM category_counts WHERE match_status = 'AMBIGUOUS'), 0),
                        'UNMATCHED', coalesce((SELECT count FROM category_counts WHERE match_status = 'UNMATCHED'), 0),
                        'NO_COORDINATES', coalesce((SELECT count FROM category_counts WHERE match_status = 'NO_COORDINATES'), 0)
                    ),
                    'filtered_event_count', (SELECT count(*) FROM classified)
                )
                """
            ),
            params,
        )
        assert isinstance(result, dict)
        return {
            "administrative_level": administrative_level,
            "grouping_method": "BOUNDARY_DERIVED_LOCATION",
            "regions": result["regions"],
            "categories": result["categories"],
            "filtered_event_count": result["filtered_event_count"],
            "applied_observation_time_range": {
                "from": filters.observed_after,
                "to": filters.observed_before,
            },
            "coverage_note": (
                "Exactly one ST_Covers match is counted by boundary; multiple matches are AMBIGUOUS. "
                "ADM1 2011 and ADM2 2021 are independent; Lakshadweep alignment is limited."
            ),
        }
