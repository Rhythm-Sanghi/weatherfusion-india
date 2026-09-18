import type { AuditEvent, EventFilters, EventListResponse, EventSummary, ReviewDetail, ReviewQueueItem, ReviewRequest, WeatherEvent } from "../types/events";

export type HealthResponse = {
  status: "ok";
  service: string;
};

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

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

export function getEventSummary(): Promise<EventSummary> {
  return request<EventSummary>("/api/v1/events/summary");
}

export function getReviewQueue(): Promise<ReviewQueueItem[]> { return request<ReviewQueueItem[]>("/api/v1/review-queue"); }
export function getReviewDetail(eventId: string): Promise<ReviewDetail> { return request<ReviewDetail>(`/api/v1/review-queue/${eventId}`); }
export function getEventAudit(eventId: string): Promise<AuditEvent[]> { return request<AuditEvent[]>(`/api/v1/events/${eventId}/audit`); }
export function submitReview(eventId: string, review: ReviewRequest): Promise<unknown> { return request(`/api/v1/events/${eventId}/reviews`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(review) }); }
export function getAnalyticsOverview(): Promise<Record<string, number>> { return request("/api/v1/analytics/overview"); }
export function getAnalyticsDistribution(): Promise<Record<string, Record<string, number>>> { return request("/api/v1/analytics/distribution"); }
export function getSources(): Promise<Array<{ id: string; name: string; source_type: string; enabled: boolean; event_count: number; last_activity: string | null; status: string }>> { return request("/api/v1/sources"); }
export function getSystemStatus(): Promise<Record<string, { status: string; implementation?: string }>> { return request("/api/v1/system/status"); }
