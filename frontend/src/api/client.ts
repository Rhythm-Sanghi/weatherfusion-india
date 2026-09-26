import type { AuditEvent, CitizenReportRequest, EventFilters, EventListResponse, EventSummary, ReviewDetail, ReviewQueueItem, ReviewRequest, WeatherEvent } from "../types/events";

export type HealthResponse = {
  status: "ok";
  service: string;
};

export type WeatherForecastContext = {
  status: "live" | "cached" | "unavailable" | "disabled" | "demo_offline";
  source: "open-meteo";
  location?: { name: string; latitude: number; longitude: number };
  observation_time?: string | null;
  retrieved_at?: string;
  cache_age_seconds?: number;
  forecast: { current?: Record<string, unknown>; current_units?: Record<string, string> } | null;
  disclaimer?: string;
};

export type NearbyEventsResponse = {
  source_event_id: string;
  radius_meters: number;
  provider: { name: string; version: string };
  items: Array<{
    id: string;
    relationship: string;
    distance_meters: number;
    observed_at: string | null;
    title: string | null;
    event_type: string | null;
    source_name: string | null;
  }>;
};

export type MapFeatureCollection = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: { type: "Point"; coordinates: [number, number] };
    properties: {
      id: string;
      event_type: string;
      severity: string;
      processing_status: string;
      system_assessment: string;
      admin_status: string;
      observed_at: string;
      source_name: string;
      source_type: string;
      origin_mode?: string | null;
    };
  }>;
};

export type GeoCluster = { cluster_id: string; event_ids: string[]; event_count: number; longitude: number; latitude: number; event_type_distribution: Record<string, number>; severity_distribution: Record<string, number>; observed_from: string; observed_to: string; method: string };
export type GeoHotspot = { cell_id: string; event_count: number; event_ids: string[]; longitude: number; latitude: number; event_type_distribution: Record<string, number>; severity_distribution: Record<string, number>; geometry: { type: "Polygon"; coordinates: number[][][] }; method: string };
export type GeoRegion = { state: string; district: string; event_count: number; grouping_method: string };
export type BoundaryFeatureCollection = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: { type: "Polygon" | "MultiPolygon"; coordinates: number[][][] | number[][][][] };
    properties: { id: string; boundary_uuid: string; name: string; source_code: string | null; dataset_id: string; vintage: number | null; license: string; attribution: string; level: "ADM1" | "ADM2" };
  }>;
};
export type BoundaryRegionalSummary = {
  administrative_level: "ADM1" | "ADM2";
  grouping_method: "BOUNDARY_DERIVED_LOCATION";
  regions: Array<{ boundary_id: string; administrative_name: string; source_administrative_code: string | null; dataset_identifier: string; dataset_administrative_vintage: number | null; event_count: number; event_type_distribution: Record<string, number>; system_assessment_distribution: Record<string, number>; admin_status_distribution: Record<string, number> }>;
  categories: { AMBIGUOUS: number; UNMATCHED: number; NO_COORDINATES: number };
  filtered_event_count: number;
  applied_observation_time_range: { from: string | null; to: string | null };
  coverage_note: string;
};
export type EventBoundaryMatches = { method: string; source_location: string; boundary_location: string; cross_vintage_note?: string; levels: Record<"ADM1" | "ADM2", { status: "MATCHED" | "AMBIGUOUS" | "UNMATCHED" | "NO_COORDINATES"; candidates: Array<{ source_feature_id: string; name: string; source_code: string | null; boundary_id: string; year_represented: number | null }> }> };

// Use the explicit IPv4 loopback address so browsers that resolve localhost to
// IPv6 (::1) can still reach the backend bound on 127.0.0.1.
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/api/health`);
  if (!response.ok) {
    throw new ApiError("The backend could not be reached.", response.status);
  }
  return (await response.json()) as HealthResponse;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new ApiError(
      body?.detail ?? (response.status === 404 ? "The requested event was not found." : "The backend could not be reached."),
      response.status,
    );
  }
  return (await response.json()) as T;
}

export async function listEvents(filters: EventFilters = {}): Promise<EventListResponse> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  return request<EventListResponse>(`/api/v1/events${query}`);
}

export function getEvent(eventId: string): Promise<WeatherEvent> {
  return request<WeatherEvent>(`/api/v1/events/${eventId}`);
}

export function getNearbyEvents(eventId: string): Promise<NearbyEventsResponse> {
  return request<NearbyEventsResponse>(`/api/v1/events/${eventId}/nearby`);
}

export function getMapEvents(filters: EventFilters & { limit?: number } = {}): Promise<MapFeatureCollection> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  return request<MapFeatureCollection>(`/api/v1/events/map/events${query}`);
}

export function getBoundaries(level: "ADM1" | "ADM2", limit: number): Promise<BoundaryFeatureCollection> {
  return request<BoundaryFeatureCollection>(`/api/v1/geo/boundaries?level=${level}&limit=${limit}&geometry_purpose=display`);
}

export function getEventBoundaries(eventId: string): Promise<EventBoundaryMatches> {
  return request<EventBoundaryMatches>(`/api/v1/geo/events/${eventId}/boundaries`);
}

function geoQuery<T>(path: string, filters: EventFilters & { hours?: number } = {}): Promise<T> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value !== undefined && value !== "") params.set(key, String(value));
  return request<T>(`${path}${params.size ? `?${params}` : ""}`);
}
export function getGeoClusters(filters: EventFilters & { hours?: number } = {}): Promise<GeoCluster[]> { return geoQuery("/api/v1/geo/clusters", filters); }
export function getGeoHotspots(filters: EventFilters & { hours?: number } = {}): Promise<GeoHotspot[]> { return geoQuery("/api/v1/geo/hotspots", filters); }
export function getGeoRegions(filters: EventFilters & { hours?: number; grouping_method?: "SOURCE_PROVIDED_LOCATION" | "BOUNDARY_DERIVED_LOCATION"; administrative_level?: "ADM1" | "ADM2" } = {}): Promise<GeoRegion[] | BoundaryRegionalSummary> { return geoQuery("/api/v1/geo/regions/summary", filters); }

export function getEventSummary(): Promise<EventSummary> {
  return request<EventSummary>("/api/v1/events/summary");
}

export function getReviewQueue(): Promise<ReviewQueueItem[]> { return request<ReviewQueueItem[]>("/api/v1/review-queue"); }
export function getReviewDetail(eventId: string): Promise<ReviewDetail> { return request<ReviewDetail>(`/api/v1/review-queue/${eventId}`); }
export function getEventAudit(eventId: string): Promise<AuditEvent[]> { return request<AuditEvent[]>(`/api/v1/events/${eventId}/audit`); }
export function submitReview(eventId: string, review: ReviewRequest): Promise<unknown> { return request(`/api/v1/events/${eventId}/reviews`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(review) }); }
export function getAnalyticsOverview(): Promise<Record<string, number>> { return request("/api/v1/analytics/overview"); }
export function getAnalyticsDistribution(): Promise<Record<string, Record<string, number>>> { return request("/api/v1/analytics/distribution"); }
export function getSources(): Promise<Array<{ id: string; name: string; source_type: string; enabled: boolean; event_count: number; last_activity: string | null; status: string; mode?: string | null; records_available?: number | null }>> { return request("/api/v1/sources"); }
export function getSystemStatus(): Promise<Record<string, { status: string; implementation?: string }>> { return request("/api/v1/system/status"); }
export function getWeatherForecast(): Promise<WeatherForecastContext> { return request("/api/v1/weather/forecast"); }
export function ingestExternalWeather(): Promise<{ mode: string; created: number; duplicates: number; failed: number }> { return request("/api/v1/ingestion/weather", { method: "POST" }); }
export function ingestControlledSocialFeed(): Promise<{ mode: string; received: number; matched: number; created: number; duplicates: number; failed: number }> { return request("/api/v1/ingestion/social", { method: "POST" }); }
export type DemoFeedPost = { post_id: string; platform: string; author_alias: string; text: string; hashtags: string[]; posted_at: string; city: string; state: string; latitude: number; longitude: number; event_type: string; severity: string; media: Array<{ media_type: string; reference: string; caption?: string }> };
export type DemoScenario = { id: string; name: string; post_count: number };
export function getDemoFeed(): Promise<{ mode: string; disclaimer: string; items: DemoFeedPost[] }> { return request("/api/v1/demo/feed"); }
export function getDemoScenarios(): Promise<DemoScenario[]> { return request("/api/v1/demo/scenarios"); }
export function activateDemoScenario(id: string): Promise<{ status: string; scenario_name?: string; created: number; duplicates: number; failed: number }> { return request(`/api/v1/demo/scenarios/${id}`, { method: "POST" }); }
export function submitCitizenReport(report: CitizenReportRequest): Promise<WeatherEvent> { return request("/api/v1/reports/citizen", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(report) }); }
