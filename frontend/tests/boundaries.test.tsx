import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { getBoundaries, getEventSummary, getGeoRegions, listEvents } from "../src/api/client";
import { SituationPage } from "../src/pages/SituationPage";

vi.mock("../src/api/client", () => ({
  getBoundaries: vi.fn(), getEventSummary: vi.fn(), getGeoRegions: vi.fn(),
  listEvents: vi.fn(), getGeoClusters: vi.fn(), getGeoHotspots: vi.fn(), getWeatherForecast: vi.fn().mockResolvedValue({ status: "unavailable", source: "open-meteo", forecast: null }),
}));
vi.mock("maplibre-gl", () => ({ default: { Map: class { addControl() { return this; } addSource() {} addLayer() {} on() { return this; } remove() {} }, Marker: class { setLngLat() { return this; } setPopup() { return this; } addTo() { return this; } }, Popup: class { setText() { return this; } }, NavigationControl: class {} } }));

const boundary = { type: "FeatureCollection" as const, features: [{ type: "Feature" as const, geometry: { type: "Polygon" as const, coordinates: [[[77, 28], [78, 28], [78, 29], [77, 28]]] }, properties: { id: "source-1", boundary_uuid: "boundary-1", name: "Test State", source_code: "TS", dataset_id: "IND-ADM1-1811400", vintage: 2011, license: "CC BY 2.5 India", attribution: "geoBoundaries", level: "ADM1" as const } }] };

function LocationProbe() {
  return <output data-testid="location">{useLocation().pathname}</output>;
}

function renderSituation() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><SituationPage /><LocationProbe /></MemoryRouter></QueryClientProvider>);
}

beforeEach(() => vi.stubEnv("VITE_MAPPLS_ACCESS_TOKEN", ""));
afterEach(() => { vi.clearAllMocks(); vi.unstubAllEnvs(); });

test("loads, selects, and clears an ADM1 boundary without replacing time filters", async () => {
  vi.mocked(getEventSummary).mockResolvedValue({ total_events: 1, by_processing_status: {}, by_system_assessment: {}, by_admin_status: {} });
  vi.mocked(listEvents).mockResolvedValue({ items: [], page: 1, page_size: 100, total: 0 });
  vi.mocked(getGeoRegions).mockResolvedValue([]);
  vi.mocked(getBoundaries).mockResolvedValue(boundary);
  renderSituation();
  await screen.findByText("Operational weather picture");
  fireEvent.click(screen.getByLabelText("Administrative boundaries"));
  await waitFor(() => expect(getBoundaries).toHaveBeenCalledWith("ADM1", 36));
  expect(screen.getByText(/CC BY 2.5 India/)).toBeInTheDocument();
  fireEvent.change(await screen.findByLabelText("Selected boundary"), { target: { value: "boundary-1" } });
  await waitFor(() => expect(listEvents).toHaveBeenLastCalledWith(expect.objectContaining({ boundary_id: "boundary-1" })));
  expect(await screen.findByText("No events within the selected boundary for this observation window.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Clear boundary filter" }));
  await waitFor(() => expect(listEvents).toHaveBeenLastCalledWith(expect.not.objectContaining({ boundary_id: expect.anything() })));
});

test("loads the bounded ADM2 overlay and renders boundary-derived regional counts", async () => {
  vi.mocked(getEventSummary).mockResolvedValue({ total_events: 1, by_processing_status: {}, by_system_assessment: {}, by_admin_status: {} });
  vi.mocked(listEvents).mockResolvedValue({ items: [], page: 1, page_size: 100, total: 0 });
  vi.mocked(getBoundaries).mockResolvedValue({ ...boundary, features: [{ ...boundary.features[0], properties: { ...boundary.features[0].properties, level: "ADM2" as const, vintage: 2021 } }] });
  vi.mocked(getGeoRegions).mockResolvedValue({ administrative_level: "ADM1", grouping_method: "BOUNDARY_DERIVED_LOCATION", regions: [{ boundary_id: "boundary-1", administrative_name: "Test State", source_administrative_code: "TS", dataset_identifier: "IND-ADM1-1811400", dataset_administrative_vintage: 2011, event_count: 2, event_type_distribution: { FLOOD: 2 }, system_assessment_distribution: {}, admin_status_distribution: {} }], categories: { AMBIGUOUS: 0, UNMATCHED: 1, NO_COORDINATES: 1 }, filtered_event_count: 4, applied_observation_time_range: { from: null, to: null }, coverage_note: "Lakshadweep coverage is independent." });
  renderSituation();
  await screen.findByText("Operational weather picture");
  fireEvent.click(screen.getByLabelText("Administrative boundaries"));
  fireEvent.change(screen.getByLabelText("Boundary level"), { target: { value: "ADM2" } });
  await waitFor(() => expect(getBoundaries).toHaveBeenCalledWith("ADM2", 100));
  expect(screen.getByText(/District display is bounded/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Boundary-derived geographic grouping" }));
  expect(await screen.findByText(/Boundary-derived geographic grouping · ADM1/)).toBeInTheDocument();
  expect(screen.getByText(/Ambiguous: 0/)).toBeInTheDocument();
});

test("Mappls event reports control uses React routing and declares unavailable overlays", async () => {
  vi.stubEnv("VITE_MAPPLS_ACCESS_TOKEN", "test-token");
  vi.mocked(getEventSummary).mockResolvedValue({ total_events: 0, by_processing_status: {}, by_system_assessment: {}, by_admin_status: {} });
  vi.mocked(listEvents).mockResolvedValue({ items: [], page: 1, page_size: 100, total: 0 });
  vi.mocked(getGeoRegions).mockResolvedValue([]);
  renderSituation();
  const eventReports = await screen.findByRole("button", { name: "Event reports" });
  expect(screen.getByRole("button", { name: "Clusters" })).toBeDisabled();
  expect(screen.getByText(/Clusters, hotspots, and boundary overlays are unavailable/)).toBeInTheDocument();
  fireEvent.click(eventReports);
  expect(screen.getByTestId("location")).toHaveTextContent("/events");
  const script = document.querySelector<HTMLScriptElement>('script[data-mappls-sdk="true"]');
  if (script) await act(async () => { fireEvent.error(script); });
});
