import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { getReviewDetail, submitReview } from "../api/client";
import { AuditTimeline } from "../components/AuditTimeline";
import { StatusBadge } from "../components/StatusBadge";
import type { ReviewAction } from "../types/events";

const reviewer = { id: "demo-reviewer-01", name: "SIH Demo Operator" };

export function ReviewWorkspacePage() {
  const { eventId = "" } = useParams();
  const queryClient = useQueryClient();
  const [action, setAction] = useState<ReviewAction | "">("");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const detail = useQuery({ queryKey: ["review-detail", eventId], queryFn: () => getReviewDetail(eventId), enabled: Boolean(eventId) });
  const decision = useMutation({ mutationFn: () => submitReview(eventId, { action: action as ReviewAction, reviewer_id: reviewer.id, reviewer_name: reviewer.name, reason, notes: notes || undefined, expected_version: detail.data!.event.version }), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["review-queue"] }); void queryClient.invalidateQueries({ queryKey: ["review-detail", eventId] }); void queryClient.invalidateQueries({ queryKey: ["event", eventId] }); void queryClient.invalidateQueries({ queryKey: ["event-summary"] }); void queryClient.invalidateQueries({ queryKey: ["events"] }); } });
  if (detail.isLoading) return <p className="empty-state">Loading review workspace…</p>;
  if (detail.isError || !detail.data) return <p className="empty-state">This event is not available for review.</p>;
  const event = detail.data.event;
  const verification = (event.metadata.machine_analysis as Record<string, unknown> | undefined)?.verification as Record<string, unknown> | undefined;
  const evidence = verification?.evidence && typeof verification.evidence === "object" && !Array.isArray(verification.evidence) ? verification.evidence as Record<string, unknown> : null;
  const components = Array.isArray(evidence?.components) ? evidence.components.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && !Array.isArray(item)) : [];
  const canSubmit = Boolean(action && reason.trim() && !decision.isPending);
  const conflict = (decision.error as { status?: number } | null)?.status === 409;
  return <section className="review-workspace"><Link className="back-link" to="/review">← Review queue</Link><header className="detail-heading"><div><p className="eyebrow">{detail.data.attention_reason}</p><h2>{event.title}</h2><p>{event.event_type.replaceAll("_", " ")} · {event.severity} · {new Date(event.observed_at).toLocaleString()}</p></div><StatusBadge label="Human decision" value={event.admin_status} /></header><div className="review-workspace-grid"><article className="detail-copy"><h3>Event</h3><p>{event.description || event.raw_text}</p><dl className="detail-facts"><div><dt>Location</dt><dd>{[event.city, event.district, event.state].filter(Boolean).join(", ") || "Not recorded"}</dd></div><div><dt>Source</dt><dd>{event.source.name} · {event.source.source_type}</dd></div><div><dt>External ID</dt><dd>{event.external_id || "Not recorded"}</dd></div></dl>{event.media_evidence?.length ? <section className="media-evidence"><h3>Media evidence</h3>{event.media_evidence.map((media) => <p key={media.id}>{media.media_type} · {media.source_name} · {media.reference}</p>)}</section> : null}<h3>System evidence</h3><StatusBadge label="Processing" value={event.processing_status} /><StatusBadge label="Machine assessment" value={event.system_assessment} />{evidence ? <section className="audit-section"><h4>Evidence ranking</h4><p>Score: {typeof evidence.score === "number" ? `${Math.round(evidence.score * 100)}%` : "Not available"} · Coverage: {typeof evidence.coverage === "number" ? `${Math.round(evidence.coverage * 100)}%` : "Not available"}</p><ul>{components.map((component) => <li key={String(component.name)}>{String(component.name).replaceAll("_", " ")}: {component.available === true ? (typeof component.contribution === "number" ? `${Math.round(component.contribution * 100)} points` : "available") : "unavailable"}</li>)}</ul></section> : null}<p>These values are displayed evidence. They do not make the human decision.</p></article><aside className="review-form"><h3>Human review</h3><label>Decision<select aria-label="Review action" value={action} onChange={(item) => setAction(item.target.value as ReviewAction)}><option value="">Choose a decision</option><option value="VERIFY">Verify</option><option value="REJECT">Reject</option><option value="ESCALATE">Escalate</option></select></label><label>Reason<textarea aria-label="Review reason" value={reason} onChange={(item) => setReason(item.target.value)} required /></label><label>Notes (optional)<textarea aria-label="Review notes" value={notes} onChange={(item) => setNotes(item.target.value)} /></label><button disabled={!canSubmit} onClick={() => { if (window.confirm(`Submit ${action.toLowerCase()} decision?`)) decision.mutate(); }}>Confirm and submit</button>{decision.isSuccess && <p className="success-message">Decision saved. The event status and audit history are updated.</p>}{decision.isError && <p className="error-message">{conflict ? "This event changed after you opened it. Refresh before submitting a decision." : "Unable to save the decision."}</p>}</aside></div><section className="audit-section"><p className="eyebrow">Audit history</p><h3>Human decision trail</h3><AuditTimeline entries={detail.data.audit} /></section></section>;
}
