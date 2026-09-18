import type { AuditEvent } from "../types/events";

export function AuditTimeline({ entries }: { entries: AuditEvent[] }) {
  if (!entries.length) return <p className="audit-empty">No human decisions have been recorded.</p>;
  return <ol className="audit-timeline">{entries.map((entry) => <li key={entry.id}><strong>{entry.action.replaceAll("_", " ")}</strong><span>{entry.actor_name} · {new Date(entry.created_at).toLocaleString()}</span><p>{entry.previous_value ?? "—"} → {entry.new_value ?? "—"}{entry.reason ? ` · ${entry.reason}` : ""}</p></li>)}</ol>;
}
