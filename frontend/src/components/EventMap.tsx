import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { WeatherEvent } from "../types/events";

type EventMapProps = { events: WeatherEvent[]; compact?: boolean };

function markerColor(severity: string): string {
  if (severity === "CRITICAL") return "#a9342b";
  if (severity === "HIGH") return "#d06a2c";
  if (severity === "MODERATE") return "#b08a1a";
  return "#277f8e";
}

export function EventMap({ events, compact = false }: EventMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const [mapError, setMapError] = useState(false);

  useEffect(() => {
    if (!container.current) return;
    let map: maplibregl.Map | undefined;
    try {
      map = new maplibregl.Map({
        container: container.current,
        style: "https://demotiles.maplibre.org/style.json",
        center: [78.9629, 22.5937],
        zoom: compact ? 3.2 : 3.8,
      });
      map.addControl(new maplibregl.NavigationControl(), "top-right");
      for (const event of events) {
        if (event.longitude === null || event.latitude === null) continue;
        new maplibregl.Marker({ color: markerColor(event.severity) })
          .setLngLat([event.longitude, event.latitude])
          .setPopup(new maplibregl.Popup({ offset: 18 }).setText(`${event.title} — ${event.event_type.replaceAll("_", " ")}`))
          .addTo(map);
      }
      map.on("error", () => setMapError(true));
    } catch {
      setMapError(true);
    }
    return () => map?.remove();
  }, [compact, events]);

  return (
    <div className={`map-frame${compact ? " map-frame-compact" : ""}`}>
      <div aria-label="India event display map" className="map-canvas" ref={container} />
      {mapError && <p className="map-notice">Basemap unavailable. Event markers will be available when a map provider is connected.</p>}
    </div>
  );
}
