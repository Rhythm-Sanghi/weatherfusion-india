import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";

import { getEvent, getEventSummary, getWeatherForecast, listEvents } from "../src/api/client";
import { EventDetailPage } from "../src/pages/EventDetailPage";
import { EventsPage } from "../src/pages/EventsPage";
import { MapPage } from "../src/pages/MapPage";
import { SituationPage } from "../src/pages/SituationPage";
import type { WeatherEvent } from "../src/types/events";

vi.mock("../src/api/client", () => ({
  getEvent: vi.fn(),
  getEventSummary: vi.fn(),
  getWeatherForecast: vi.fn().mockResolvedValue({ status: "unavailable", source: "open-meteo", forecast: null }),
  listEvents: vi.fn(),
}));

vi.mock("maplibre-gl", () => ({
  default: {
    Map: class { addControl() { return this; } on() { return this; } remove() {} },
    Marker: class { setLngLat() { return this; } setPopup() { return this; } addTo() { return this; } },
    Popup: class { setText() { return this; } },
    NavigationControl: class {},
  },
}));

const mockedListEvents = vi.mocked(listEvents);
const mockedGetEvent = vi.mocked(getEvent);
const mockedGetEventSummary = vi.mocked(getEventSummary);
const mockedGetWeatherForecast = vi.mocked(getWeatherForecast);

const event: WeatherEvent = {
  id: "event-1", external_id: "demo-001", event_type: "FLOOD", severity: "HIGH", title: "Flood report", description: "A curated report.", raw_text: "Flood report", latitude: 26.1, longitude: 91.7, state: "Assam", district: "Kamrup", city: "Guwahati", observed_at: "2026-09-19T06:00:00Z", received_at: "2026-09-19T06:00:00Z", created_at: "2026-09-19T06:00:00Z", updated_at: "2026-09-19T06:00:00Z", processing_status: "COMPLETE", system_assessment: "NEEDS_REVIEW", admin_status: "UNREVIEWED", version: 1, metadata: {}, source: { id: "source-1", name: "Demo", source_type: "DEMO", reliability: null, enabled: true },
};

function renderPage(page: React.ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><MemoryRouter>{page}</MemoryRouter></QueryClientProvider>);
}

afterEach(() => vi.clearAllMocks());

test("situation renders API summary and recent events", async () => {
  mockedGetEventSummary.mockResolvedValue({ total_events: 1, by_processing_status: { PARTIAL: 0 }, by_system_assessment: { NEEDS_REVIEW: 1 }, by_admin_status: {} });
  mockedListEvents.mockResolvedValue({ items: [event], page: 1, page_size: 8, total: 1 });
  renderPage(<SituationPage />);
  expect(await screen.findByText("Operational weather picture")).toBeInTheDocument();
  expect(screen.getByText("Flood report")).toBeInTheDocument();
});

test("situation keeps a loading state while API data is pending", () => {
  mockedGetEventSummary.mockReturnValue(new Promise(() => {}));
  mockedListEvents.mockReturnValue(new Promise(() => {}));
  renderPage(<SituationPage />);
  expect(screen.getByText("Loading national situation…")).toBeInTheDocument();
});

test("situation shows API failure", async () => {
  mockedGetEventSummary.mockRejectedValue(new Error("offline"));
  mockedListEvents.mockRejectedValue(new Error("offline"));
  renderPage(<SituationPage />);
  expect(await screen.findByText("Situation unavailable")).toBeInTheDocument();
});

test("situation labels demo-offline forecast data without presenting it as live", async () => {
  mockedGetEventSummary.mockResolvedValue({ total_events: 0, by_processing_status: {}, by_system_assessment: {}, by_admin_status: {} });
  mockedListEvents.mockResolvedValue({ items: [], page: 1, page_size: 100, total: 0 });
  mockedGetWeatherForecast.mockResolvedValue({ status: "demo_offline", source: "open-meteo", forecast: null });
  renderPage(<SituationPage />);
  expect(await screen.findByText(/demo offline; no live forecast is being displayed/)).toBeInTheDocument();
});

test("explorer loads events and applies a category filter", async () => {
  mockedListEvents.mockResolvedValue({ items: [event], page: 1, page_size: 10, total: 1 });
  renderPage(<EventsPage />);
  expect(await screen.findByText("Flood report")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Event category"), { target: { value: "FLOOD" } });
  await waitFor(() => expect(mockedListEvents).toHaveBeenLastCalledWith(expect.objectContaining({ event_type: "FLOOD" })));
});

test("detail renders an event and its separate status fields", async () => {
  mockedGetEvent.mockResolvedValue(event);
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={["/events/event-1"]}><Routes><Route path="/events/:eventId" element={<EventDetailPage />} /></Routes></MemoryRouter></QueryClientProvider>);
  expect(await screen.findByText("Flood report")).toBeInTheDocument();
  expect(screen.getByText("CITIZEN REPORT")).toBeInTheDocument();
  expect(screen.getByText("System assessment")).toBeInTheDocument();
});

test("detail shows a not-found style error", async () => {
  mockedGetEvent.mockRejectedValue(new Error("not found"));
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={["/events/missing"]}><Routes><Route path="/events/:eventId" element={<EventDetailPage />} /></Routes></MemoryRouter></QueryClientProvider>);
  expect(await screen.findByText("Event not available")).toBeInTheDocument();
});

test("map page renders with event data", async () => {
  mockedListEvents.mockResolvedValue({ items: [event], page: 1, page_size: 100, total: 1 });
  renderPage(<MapPage />);
  expect(await screen.findByLabelText("India event display map")).toBeInTheDocument();
});
