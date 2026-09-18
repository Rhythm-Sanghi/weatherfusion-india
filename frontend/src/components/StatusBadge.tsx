type StatusBadgeProps = { label: string; value: string };

export function StatusBadge({ label, value }: StatusBadgeProps) {
  const tone = value === "FAILED" || value === "DISPUTED" || value === "REJECTED" ? "danger" : value === "PARTIAL" || value === "NEEDS_REVIEW" || value === "UNAVAILABLE" || value === "ESCALATED" ? "warning" : "neutral";
  return <span className={`status-badge status-${tone}`}><span>{label}</span>{value.replaceAll("_", " ")}</span>;
}
