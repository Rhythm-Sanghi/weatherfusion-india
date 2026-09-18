import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";

import { getReviewDetail, getReviewQueue, submitReview } from "../src/api/client";
import { ReviewQueuePage } from "../src/pages/ReviewQueuePage";
import { ReviewWorkspacePage } from "../src/pages/ReviewWorkspacePage";

vi.mock("../src/api/client", () => ({
  ApiError: class ApiError extends Error { constructor(message: string, public status?: number) { super(message); } },
  getReviewDetail: vi.fn(), getReviewQueue: vi.fn(), submitReview: vi.fn(),
}));

const queue = vi.mocked(getReviewQueue); const detail = vi.mocked(getReviewDetail); const submit = vi.mocked(submitReview);
const event = { id: "event-1", external_id: "demo-1", event_type: "FLOOD", severity: "HIGH", title: "Flood report", description: "Report text", raw_text: "Report text", latitude: 1, longitude: 2, state: "Assam", district: "Kamrup", city: "Guwahati", observed_at: "2026-09-19T06:00:00Z", received_at: "2026-09-19T06:00:00Z", created_at: "2026-09-19T06:00:00Z", updated_at: "2026-09-19T06:00:00Z", processing_status: "PARTIAL", system_assessment: "NEEDS_REVIEW", admin_status: "UNREVIEWED", version: 1, metadata: {}, source: { id: "source", name: "Demo", source_type: "DEMO", reliability: null, enabled: true } } as const;
function wrap(page: React.ReactNode) { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{page}</MemoryRouter></QueryClientProvider>); }
function workspace() { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={["/review/event-1"]}><Routes><Route path="/review/:eventId" element={<ReviewWorkspacePage />} /></Routes></MemoryRouter></QueryClientProvider>); }
afterEach(() => { vi.resetAllMocks(); vi.restoreAllMocks(); });

test("review queue loads events and handles its empty state", async () => { queue.mockResolvedValue([{ ...event, attention_reason: "Needs Review" }]); wrap(<ReviewQueuePage />); expect(await screen.findByText("Flood report")).toBeInTheDocument(); queue.mockResolvedValue([]); wrap(<ReviewQueuePage />); expect(await screen.findByText("No unreviewed events require attention.")).toBeInTheDocument(); });
test("review workspace requires a reason and updates after success", async () => { detail.mockResolvedValue({ event, attention_reason: "Needs review", audit: [] }); submit.mockResolvedValue({}); vi.spyOn(window, "confirm").mockReturnValue(true); workspace(); expect(await screen.findByText("Flood report")).toBeInTheDocument(); expect(screen.getByRole("button", { name: "Confirm and submit" })).toBeDisabled(); fireEvent.change(screen.getByLabelText("Review action"), { target: { value: "VERIFY" } }); fireEvent.change(screen.getByLabelText("Review reason"), { target: { value: "Reviewed evidence" } }); fireEvent.click(screen.getByRole("button", { name: "Confirm and submit" })); expect(await screen.findByText("Decision saved. The event status and audit history are updated.")).toBeInTheDocument(); });
test("review workspace presents a conflict message", async () => { detail.mockResolvedValue({ event, attention_reason: "Needs review", audit: [] }); submit.mockRejectedValue({ status: 409 }); vi.spyOn(window, "confirm").mockReturnValue(true); workspace(); await screen.findByText("Flood report"); fireEvent.change(screen.getByLabelText("Review action"), { target: { value: "VERIFY" } }); fireEvent.change(screen.getByLabelText("Review reason"), { target: { value: "Reviewed evidence" } }); fireEvent.click(screen.getByRole("button", { name: "Confirm and submit" })); await waitFor(() => expect(screen.getByText("This event changed after you opened it. Refresh before submitting a decision.")).toBeInTheDocument()); });
