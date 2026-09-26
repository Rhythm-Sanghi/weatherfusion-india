import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";

import { submitCitizenReport } from "../src/api/client";
import { CitizenReportPage } from "../src/pages/CitizenReportPage";

vi.mock("../src/api/client", () => ({ submitCitizenReport: vi.fn() }));
const submit = vi.mocked(submitCitizenReport);

function renderPage() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={["/reports/citizen"]}><Routes><Route path="/reports/citizen" element={<CitizenReportPage />} /><Route path="/events/:eventId" element={<p>Created event</p>} /></Routes></MemoryRouter></QueryClientProvider>);
}

afterEach(() => vi.resetAllMocks());

test("citizen report validates description and coordinates before submission", () => {
  renderPage();
  fireEvent.click(screen.getByRole("button", { name: "Submit weather report" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Describe the weather observation");
  fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Waterlogging near the road" } });
  fireEvent.change(screen.getByLabelText("Latitude"), { target: { value: "91" } });
  fireEvent.change(screen.getByLabelText("Longitude"), { target: { value: "72" } });
  fireEvent.click(screen.getByRole("button", { name: "Submit weather report" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Enter valid latitude and longitude");
  expect(submit).not.toHaveBeenCalled();
});

test("citizen report submits controlled input and opens the created event", async () => {
  submit.mockResolvedValue({ id: "created-1" } as never);
  renderPage();
  fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Heavy rainfall with waterlogging near the road." } });
  fireEvent.change(screen.getByLabelText("Latitude"), { target: { value: "19.076" } });
  fireEvent.change(screen.getByLabelText("Longitude"), { target: { value: "72.8777" } });
  fireEvent.change(screen.getByLabelText("City"), { target: { value: "Mumbai" } });
  fireEvent.change(screen.getByLabelText("Media reference"), { target: { value: "demo://media/citizen.jpg" } });
  fireEvent.click(screen.getByRole("button", { name: "Submit weather report" }));
  await waitFor(() => expect(submit.mock.calls[0]?.[0]).toEqual(expect.objectContaining({ description: "Heavy rainfall with waterlogging near the road.", latitude: 19.076, longitude: 72.8777, city: "Mumbai", media: [{ media_type: "IMAGE", reference: "demo://media/citizen.jpg" }] })));
  expect(await screen.findByText("Created event")).toBeInTheDocument();
});

test("citizen report shows an API failure safely", async () => {
  submit.mockRejectedValue(new Error("offline"));
  renderPage();
  fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Heavy rainfall" } });
  fireEvent.change(screen.getByLabelText("Latitude"), { target: { value: "19" } });
  fireEvent.change(screen.getByLabelText("Longitude"), { target: { value: "72" } });
  fireEvent.click(screen.getByRole("button", { name: "Submit weather report" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("could not be submitted");
});
