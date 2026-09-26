import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { BoundaryFeatureCollection, GeoCluster, GeoHotspot, MapFeatureCollection } from "../api/client";
import type { WeatherEvent } from "../types/events";

type EventMapProps = {
  events: WeatherEvent[];
  geojson?: MapFeatureCollection;
  clusters?: GeoCluster[];
  hotspots?: GeoHotspot[];
  boundaries?: BoundaryFeatureCollection;
  selectedBoundaryId?: string | null;
  onBoundarySelect?: (boundaryId: string) => void;
  compact?: boolean;
};

type MapPoint = {
  id: string;
  latitude: number;
  longitude: number;
  severity: string;
  title: string;
  eventType: string;
};

const EMPTY_CLUSTERS: GeoCluster[] = [];
const EMPTY_HOTSPOTS: GeoHotspot[] = [];

type MapplsMap = { remove?: () => void };
type MapplsSdk = {
  Map: new (container: HTMLElement, options: { center: { lat: number; lng: number }; zoom: number }) => MapplsMap;
  Marker: new (options: { map: MapplsMap; position: { lat: number; lng: number } }) => unknown;
  addGeoJson?: (options: { map: MapplsMap; data: object; fitbounds?: boolean; cType?: number }) => unknown;
};

declare global {
  interface Window {
    mappls?: MapplsSdk;
  }
}

let mapplsSdkPromise: Promise<MapplsSdk> | undefined;
let mapContainerCount = 0;

function loadMappls(accessToken: string): Promise<MapplsSdk> {
  if (mapplsSdkPromise) return mapplsSdkPromise;
  if (window.mappls) {
    mapplsSdkPromise = Promise.resolve(window.mappls);
    return mapplsSdkPromise;
  }
  document.querySelector<HTMLScriptElement>('script[data-mappls-sdk="true"]')?.remove();
  const script = document.createElement("script");
  script.dataset.mapplsSdk = "true";
  script.src = `https://sdk.mappls.com/map/sdk/web?v=3.0&access_token=${encodeURIComponent(accessToken)}`;
  const loadAttempt = new Promise<MapplsSdk>((resolve, reject) => {
    script.onload = () => window.mappls ? resolve(window.mappls) : reject(new Error("Mappls did not initialise."));
    script.onerror = () => reject(new Error("Mappls could not be loaded."));
    document.head.append(script);
  });
  mapplsSdkPromise = loadAttempt.catch((error: unknown) => {
    mapplsSdkPromise = undefined;
    script.remove();
    throw error;
  });
  return mapplsSdkPromise;
}

function markerColor(severity: string): string {
  if (severity === "CRITICAL") return "#a9342b";
  if (severity === "HIGH") return "#d06a2c";
  if (severity === "MODERATE") return "#b08a1a";
  return "#277f8e";
}

export function EventMap({ events, geojson, clusters = EMPTY_CLUSTERS, hotspots = EMPTY_HOTSPOTS, boundaries, selectedBoundaryId, onBoundarySelect, compact = false }: EventMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const mapId = useRef(`map-${++mapContainerCount}`);
  const [mapError, setMapError] = useState(false);
  const [mapProviderFallback, setMapProviderFallback] = useState(false);
  const mapGeojson = compact ? undefined : geojson;

  useEffect(() => {
    const target = container.current;
    if (!target) return;
    target.replaceChildren();
    let map: maplibregl.Map | undefined;
    let mapplsMap: MapplsMap | undefined;
    let disposed = false;
    const useMappls = Boolean(import.meta.env.VITE_MAPPLS_ACCESS_TOKEN);
    setMapProviderFallback(false);
    const points: MapPoint[] = mapGeojson && mapGeojson.features.length > 0
      ? mapGeojson.features.map((feature) => ({
        id: feature.properties.id,
        longitude: feature.geometry.coordinates[0],
        latitude: feature.geometry.coordinates[1],
        severity: feature.properties.severity,
        title: feature.properties.source_name || feature.properties.event_type,
        eventType: feature.properties.event_type,
      }))
      : events
        .filter((event) => event.longitude !== null && event.latitude !== null)
        .map((event) => ({
          id: event.id,
          longitude: event.longitude as number,
          latitude: event.latitude as number,
          severity: event.severity,
          title: event.title,
          eventType: event.event_type,
        }));
    const createMap = async () => {
      if (useMappls) {
        try {
          const mappls = await loadMappls(import.meta.env.VITE_MAPPLS_ACCESS_TOKEN);
          if (disposed) return;
          mapplsMap = new mappls.Map(target, {
            center: { lat: 22.5937, lng: 78.9629 },
            // Keep Mappls initialization identical in both map surfaces. Its Web SDK
            // rejects the compact-only zoom value in some browser sessions.
            zoom: 3.8,
          });
          for (const point of points) {
            new mappls.Marker({ map: mapplsMap, position: { lat: point.latitude, lng: point.longitude } });
          }
          for (const cluster of clusters) {
            new mappls.Marker({ map: mapplsMap, position: { lat: cluster.latitude, lng: cluster.longitude } });
          }
          if (hotspots.length) {
            mappls.addGeoJson?.({
              map: mapplsMap,
              data: {
                type: "FeatureCollection",
                features: hotspots.map((hotspot) => ({ type: "Feature", geometry: hotspot.geometry, properties: { count: hotspot.event_count, fill: "#d06a2c", "fill-opacity": 0.32 } })),
              },
              fitbounds: false,
              cType: 0,
            });
          }
          if (boundaries) {
            mappls.addGeoJson?.({
              map: mapplsMap,
              data: boundaries,
              fitbounds: false,
              cType: 0,
            });
          }
          return;
        } catch {
          if (disposed) return;
          setMapProviderFallback(true);
        }
      }
      if (disposed) return;
      try {
      map = new maplibregl.Map({
        container: target,
        style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        center: [78.9629, 22.5937],
        zoom: compact ? 3.2 : 3.8,
      });
      map.addControl(new maplibregl.NavigationControl(), "top-right");
      for (const point of points) {
        new maplibregl.Marker({ color: markerColor(point.severity) })
          .setLngLat([point.longitude, point.latitude])
          .setPopup(new maplibregl.Popup({ offset: 18 }).setText(`${point.title} — ${point.eventType.replaceAll("_", " ")}`))
          .addTo(map);
      }
      for (const cluster of clusters) {
        new maplibregl.Marker({ color: "#5940a8" })
          .setLngLat([cluster.longitude, cluster.latitude])
          .setPopup(new maplibregl.Popup({ offset: 18 }).setText(`${cluster.event_count} submitted reports · cluster`))
          .addTo(map);
      }
      if (hotspots.length) {
        map.on("load", () => {
          map?.addSource("hotspots", { type: "geojson", data: { type: "FeatureCollection", features: hotspots.map((hotspot) => ({ type: "Feature", geometry: hotspot.geometry, properties: { count: hotspot.event_count } })) } });
          map?.addLayer({ id: "hotspot-cells", type: "fill", source: "hotspots", paint: { "fill-color": "#d06a2c", "fill-opacity": 0.32, "fill-outline-color": "#a9342b" } });
        });
      }
      if (boundaries) {
        map.on("load", () => {
          const data = {
            ...boundaries,
            features: boundaries.features.map((feature) => ({
              ...feature,
              properties: { ...feature.properties, selected: feature.properties.boundary_uuid === selectedBoundaryId },
            })),
          };
          map?.addSource("administrative-boundaries", { type: "geojson", data: data as maplibregl.GeoJSONSourceSpecification["data"] });
          map?.addLayer({ id: "administrative-boundary-fill", type: "fill", source: "administrative-boundaries", paint: { "fill-color": ["case", ["get", "selected"], "#5940a8", "#d06a2c"], "fill-opacity": ["case", ["get", "selected"], 0.34, 0.12] } });
          map?.addLayer({ id: "administrative-boundary-line", type: "line", source: "administrative-boundaries", paint: { "line-color": ["case", ["get", "selected"], "#39296f", "#9b5327"], "line-width": ["case", ["get", "selected"], 2.5, 1] } });
          if (onBoundarySelect) {
            map?.on("click", "administrative-boundary-fill", (event) => {
              const boundaryId = event.features?.[0]?.properties?.boundary_uuid;
              if (boundaryId) onBoundarySelect(boundaryId);
            });
          }
        });
      }
      map.on("error", () => setMapError(true));
    } catch {
      setMapError(true);
    }
    };
    void createMap();
    return () => {
      disposed = true;
      map?.remove();
      mapplsMap?.remove?.();
      target.replaceChildren();
    };
  }, [boundaries, clusters, compact, events, mapGeojson, hotspots, onBoundarySelect, selectedBoundaryId]);

  return (
    <div className={`map-frame${compact ? " map-frame-compact" : ""}`}>
      <div aria-label="India event display map" className="map-canvas" id={mapId.current} ref={container} />
      {mapProviderFallback && <p className="map-notice">Mappls could not be loaded; showing the fallback basemap.</p>}
      {mapError && <p className="map-notice">Basemap unavailable. Event markers will be available when a map provider is connected.</p>}
    </div>
  );
}
