import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getReviewQueue } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";

export function ReviewQueuePage() {
  const queue = useQuery({ queryKey: ["review-queue"], queryFn: getReviewQueue });
  if (queue.isLoading) return <p className="empty-state">Loading review queue…</p>;
  if (queue.isError || !queue.data) return <p className="empty-state">Unable to load the review queue. Check the API connection and retry.</p>;
  return <section className="review-page"><header className="page-heading"><p className="eyebrow">Human review queue</p><h2>Events requiring operator attention</h2><p>Prioritized unreviewed reports. System assessment is evidence only; a human records every decision.</p></header>{queue.data.length === 0 ? <p className="empty-state">No unreviewed events require attention.</p> : <div className="review-list">{queue.data.map((event) => <article key={event.id} className="review-card"><div><p className="eyebrow">{event.attention_reason}</p><h3><Link to={`/review/${event.id}`}>{event.title}</Link></h3><p>{event.city ?? "Location pending"}, {event.state ?? "state pending"} · {new Date(event.observed_at).toLocaleString()} · {event.source.name}</p></div><div className="review-statuses"><StatusBadge label="Processing" value={event.processing_status} /><StatusBadge label="Machine" value={event.system_assessment} /><StatusBadge label="Human" value={event.admin_status} /></div><Link className="review-open" to={`/review/${event.id}`}>Review event</Link></article>)}</div>}</section>;
}
