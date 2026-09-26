import { useQuery } from "@tanstack/react-query";

import { getMapEvents, listEvents } from "../api/client";
import { EventMap } from "../components/EventMap";

export function MapPage() {
  const events = useQuery({ queryKey: ["events", "map"], queryFn: () => listEvents({ page_size: 100 }) });
  const map = useQuery({ queryKey: ["map-events"], queryFn: () => getMapEvents({ limit: 500 }) });
  const usesMappls = Boolean(import.meta.env.VITE_MAPPLS_ACCESS_TOKEN);
  return <section className="map-page"><header className="page-heading"><p className="eyebrow">Live map</p><h2>Reported event locations</h2><p>Markers show persisted coordinates only. This display does not infer locations, distances, or hotspots.</p></header>{events.isLoading ? <p className="empty-state">Loading event locations…</p> : events.isError || !events.data ? <p className="empty-state">Unable to load event locations. Check the API connection and retry.</p> : <><EventMap events={events.data.items} geojson={map.data} />{usesMappls ? <p className="map-legend map-legend-note">Mappls marker icons identify persisted reports; severity remains available in the event register.</p> : <p className="map-legend"><span className="legend-dot critical" />Critical <span className="legend-dot high" />High <span className="legend-dot moderate" />Moderate <span className="legend-dot low" />Low</p>}{map.isError && <p className="map-notice">Spatial markers are temporarily unavailable; the event register remains available.</p>}</>}</section>;
}
