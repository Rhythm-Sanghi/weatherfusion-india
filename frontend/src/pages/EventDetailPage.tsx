import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { getEvent, getEventAudit } from "../api/client";
import { AuditTimeline } from "../components/AuditTimeline";
import { StatusBadge } from "../components/StatusBadge";

function display(value: string | null): string {
  return value || "Not recorded";
}

export function EventDetailPage() {
  const { eventId = "" } = useParams();
  const event = useQuery({ queryKey: ["event", eventId], queryFn: () => getEvent(eventId), enabled: Boolean(eventId) });
  const audit = useQuery({ queryKey: ["event-audit", eventId], queryFn: () => getEventAudit(eventId), enabled: Boolean(eventId) });

  if (event.isLoading) return <p className="empty-state">Loading event record…</p>;
  if (event.isError || !event.data) return <section className="page-panel"><h2>Event not available</h2><p>The record could not be found or loaded from the API.</p><Link to="/events">Return to explorer</Link></section>;

  const record = event.data;
  return <section className="event-detail"><Link className="back-link" to="/events">← Event explorer</Link><header className="detail-heading"><div><p className="eyebrow">{record.event_type.replaceAll("_", " ")}</p><h2>{record.title}</h2><p>{new Date(record.observed_at).toLocaleString()} · {display(record.city)}, {display(record.state)}</p></div><strong className={`severity severity-${record.severity.toLowerCase()}`}>{record.severity}</strong></header><div className="detail-layout"><article className="detail-copy"><h3>Report</h3><p>{record.description || record.raw_text}</p><dl className="detail-facts"><div><dt>Source</dt><dd>{record.source.name}</dd></div><div><dt>Location</dt><dd>{[record.city, record.district, record.state].filter(Boolean).join(", ") || "Not recorded"}</dd></div><div><dt>Coordinates</dt><dd>{record.latitude === null || record.longitude === null ? "Not recorded" : `${record.latitude.toFixed(4)}, ${record.longitude.toFixed(4)}`}</dd></div><div><dt>Received</dt><dd>{new Date(record.received_at).toLocaleString()}</dd></div></dl></article><aside className="status-panel"><h3>Operational state</h3><StatusBadge label="Processing" value={record.processing_status} /><StatusBadge label="System assessment" value={record.system_assessment} /><StatusBadge label="Human review" value={record.admin_status} /><p>These statuses describe separate workflow dimensions.</p></aside></div><section className="audit-section"><p className="eyebrow">Audit history</p><h3>Human decision trail</h3>{audit.isLoading ? <p>Loading audit history…</p> : audit.isError || !audit.data ? <p className="audit-empty">Audit history is unavailable.</p> : <AuditTimeline entries={audit.data} />}</section></section>;
}
