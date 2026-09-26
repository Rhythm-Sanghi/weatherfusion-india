import { useQuery } from "@tanstack/react-query";

import { getSystemStatus } from "../api/client";

export function SystemPage() {
  const health = useQuery({ queryKey: ["system-status"], queryFn: getSystemStatus, retry: false });
  const label = health.isPending
    ? "Checking API connection"
    : health.isError
      ? "Backend unreachable"
      : "Operational";

  return (
    <section className="page-panel" aria-labelledby="system-title">
      <p className="eyebrow">System status</p>
      <h2 id="system-title">Service readiness</h2>
      <p>Live API, database, and prototype adapter readiness.</p>
      <dl className="status-list">
        <div>
          <dt>API</dt>
          <dd className={health.isError ? "status-error" : "status-ok"}>{label}</dd>
        </div>
        <div>
          <dt>Service</dt>
          <dd>{health.data?.database?.status ?? "Awaiting response"}</dd>
        </div>
        <div><dt>Verification Adapter</dt><dd>{health.data?.verification_provider?.implementation ? `${health.data.verification_provider.status} (${health.data.verification_provider.implementation})` : "Awaiting response"}</dd></div>
        <div><dt>Geospatial Adapter</dt><dd>{health.data?.geospatial_provider?.implementation ? `${health.data.geospatial_provider.status} (${health.data.geospatial_provider.implementation})` : "Awaiting response"}</dd></div>
      </dl>
      {health.isError && <p className="status-note">Start the backend and refresh this page.</p>}
    </section>
  );
}
