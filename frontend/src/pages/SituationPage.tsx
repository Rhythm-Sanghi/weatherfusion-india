import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getEventSummary, listEvents } from "../api/client";
import { EventMap } from "../components/EventMap";
import { StatusBadge } from "../components/StatusBadge";

export function SituationPage() {
  const summary = useQuery({ queryKey: ["event-summary"], queryFn: getEventSummary });
  const events = useQuery({ queryKey: ["events", "situation"], queryFn: () => listEvents({ page_size: 8 }) });
  if (summary.isLoading || events.isLoading) return <section className="page-panel"><p>Loading national situation…</p></section>;
  if (summary.isError || events.isError || !summary.data || !events.data) return <section className="page-panel"><h2>Situation unavailable</h2><p>Unable to load operational data. Confirm the backend is running and try again.</p></section>;
  const data = summary.data;
  const recent = events.data.items;
  const attention = (data.by_system_assessment.NEEDS_REVIEW ?? 0) + (data.by_processing_status.PARTIAL ?? 0);

  return <section className="situation-page">
    <header className="page-heading"><p className="eyebrow">National situation</p><h2>Operational weather picture</h2><p>Current reports from connected sources, with automated assessment and human status shown separately.</p></header>
    <div className="situation-grid">
      <div className="situation-map"><EventMap events={recent} compact /></div>
      <aside className="attention-panel"><p className="eyebrow">Attention</p><strong className="event-total">{attention}</strong><p>reports currently need an operator’s attention</p><dl className="metric-list"><div><dt>All events</dt><dd>{data.total_events}</dd></div><div><dt>Needs review</dt><dd>{data.by_system_assessment.NEEDS_REVIEW ?? 0}</dd></div><div><dt>Partial processing</dt><dd>{data.by_processing_status.PARTIAL ?? 0}</dd></div></dl></aside>
    </div>
    <section className="event-section"><div className="section-heading"><div><p className="eyebrow">Latest events</p><h3>Recent operational reports</h3></div><Link to="/events">Open explorer</Link></div>{recent.length === 0 ? <p className="empty-state">No events have been ingested yet.</p> : <div className="event-table-wrap"><table><thead><tr><th>Event</th><th>Location</th><th>System</th><th>Human review</th><th>Observed</th></tr></thead><tbody>{recent.map((event) => <tr key={event.id}><td><Link to={`/events/${event.id}`}>{event.title}</Link><small>{event.event_type.replaceAll("_", " ")}</small></td><td>{event.city ?? event.state ?? "Location pending"}</td><td><StatusBadge label="Assessment" value={event.system_assessment} /></td><td><StatusBadge label="Review" value={event.admin_status} /></td><td>{new Date(event.observed_at).toLocaleString()}</td></tr>)}</tbody></table></div>}</section>
  </section>;
}
