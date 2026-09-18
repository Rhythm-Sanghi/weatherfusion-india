export type EventCategory =
  | "HEAVY_RAINFALL"
  | "FLOOD"
  | "THUNDERSTORM"
  | "HEATWAVE"
  | "FOG"
  | "DUST_STORM"
  | "STRONG_WIND"
  | "UNKNOWN";

export type ProcessingStatus = "RECEIVED" | "PROCESSING" | "COMPLETE" | "PARTIAL" | "FAILED";
export type SystemAssessment = "PENDING" | "CORROBORATED" | "NEEDS_REVIEW" | "DISPUTED" | "UNAVAILABLE";
export type AdminStatus = "UNREVIEWED" | "VERIFIED" | "REJECTED" | "ESCALATED";

export type Source = { id: string; name: string; source_type: string; reliability: number | null; enabled: boolean };

export type WeatherEvent = {
  id: string;
  external_id: string | null;
  event_type: EventCategory;
  severity: string;
  title: string;
  description: string | null;
  raw_text: string;
  latitude: number | null;
  longitude: number | null;
  state: string | null;
  district: string | null;
  city: string | null;
  observed_at: string;
  received_at: string;
  created_at: string;
  updated_at: string;
  processing_status: ProcessingStatus;
  system_assessment: SystemAssessment;
  admin_status: AdminStatus;
  version: number;
  metadata: Record<string, unknown>;
  source: Source;
};

export type EventFilters = Partial<Pick<WeatherEvent, "event_type" | "severity" | "processing_status" | "system_assessment" | "admin_status">> & {
  state?: string;
  page?: number;
  page_size?: number;
};

export type EventListResponse = { items: WeatherEvent[]; page: number; page_size: number; total: number };
export type EventSummary = {
  total_events: number;
  by_processing_status: Record<string, number>;
  by_system_assessment: Record<string, number>;
  by_admin_status: Record<string, number>;
};

export type ReviewAction = "VERIFY" | "REJECT" | "ESCALATE";
export type AuditEvent = { id: string; event_id: string; event_type: string; action: string; actor_type: string; actor_id: string; actor_name: string; previous_value: string | null; new_value: string | null; reason: string | null; created_at: string };
export type ReviewQueueItem = WeatherEvent & { attention_reason: string };
export type ReviewDetail = { event: WeatherEvent; attention_reason: string; audit: AuditEvent[] };
export type ReviewRequest = { action: ReviewAction; reviewer_id: string; reviewer_name: string; reason: string; notes?: string; expected_version: number };
