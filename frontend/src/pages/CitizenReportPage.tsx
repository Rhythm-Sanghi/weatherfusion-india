import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { submitCitizenReport } from "../api/client";
import type { CitizenReportRequest } from "../types/events";

const categories = ["", "HEAVY_RAINFALL", "FLOOD", "THUNDERSTORM", "HEATWAVE", "FOG", "DUST_STORM", "STRONG_WIND", "UNKNOWN"];
const severities = ["", "LOW", "MODERATE", "HIGH", "CRITICAL"];

function localDateTime(): string {
  const date = new Date();
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}

export function CitizenReportPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [form, setForm] = useState({ description: "", event_type: "", severity: "", latitude: "", longitude: "", observed_at: localDateTime(), state: "", district: "", city: "", reporter_alias: "", media_type: "IMAGE", media_reference: "", media_caption: "" });
  const mutation = useMutation({
    mutationFn: submitCitizenReport,
    onSuccess: (event) => {
      void queryClient.invalidateQueries({ queryKey: ["events"] });
      void queryClient.invalidateQueries({ queryKey: ["event-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["analytics"] });
      navigate(`/events/${event.id}`);
    },
  });
  const update = (field: keyof typeof form, value: string) => setForm((current) => ({ ...current, [field]: value }));

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const latitude = Number(form.latitude);
    const longitude = Number(form.longitude);
    if (!form.description.trim()) return setError("Describe the weather observation before submitting.");
    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90 || !Number.isFinite(longitude) || longitude < -180 || longitude > 180) return setError("Enter valid latitude and longitude coordinates.");
    setError("");
    const report: CitizenReportRequest = {
      description: form.description.trim(), latitude, longitude, observed_at: new Date(form.observed_at).toISOString(),
      ...(form.event_type ? { event_type: form.event_type as CitizenReportRequest["event_type"] } : {}),
      ...(form.severity ? { severity: form.severity } : {}),
      ...(form.state.trim() ? { state: form.state.trim() } : {}), ...(form.district.trim() ? { district: form.district.trim() } : {}),
      ...(form.city.trim() ? { city: form.city.trim() } : {}), ...(form.reporter_alias.trim() ? { reporter_alias: form.reporter_alias.trim() } : {}),
      ...(form.media_reference.trim() ? { media: [{ media_type: form.media_type as "IMAGE" | "VIDEO", reference: form.media_reference.trim(), ...(form.media_caption.trim() ? { caption: form.media_caption.trim() } : {}) }] } : {}),
    };
    mutation.mutate(report);
  }

  return <section className="citizen-report-page">
    <Link className="back-link" to="/">← Situation</Link>
    <header className="page-heading"><p className="eyebrow">Controlled input</p><h2>Submit a weather report</h2><p>This form records a report for operator review. It does not verify or classify the observation.</p></header>
    <form className="citizen-report-form" onSubmit={submit}>
      <label>Description *<textarea aria-label="Description" value={form.description} onChange={(event) => update("description", event.target.value)} /></label>
      <div className="report-grid"><label>Event type<select aria-label="Event type" value={form.event_type} onChange={(event) => update("event_type", event.target.value)}>{categories.map((value) => <option key={value} value={value}>{value ? value.replaceAll("_", " ") : "Not specified"}</option>)}</select></label><label>Severity<select aria-label="Severity" value={form.severity} onChange={(event) => update("severity", event.target.value)}>{severities.map((value) => <option key={value} value={value}>{value || "Not specified"}</option>)}</select></label></div>
      <div className="report-grid"><label>Latitude *<input aria-label="Latitude" type="number" step="any" value={form.latitude} onChange={(event) => update("latitude", event.target.value)} /></label><label>Longitude *<input aria-label="Longitude" type="number" step="any" value={form.longitude} onChange={(event) => update("longitude", event.target.value)} /></label></div>
      <label>Observed at *<input aria-label="Observed at" type="datetime-local" value={form.observed_at} onChange={(event) => update("observed_at", event.target.value)} required /></label>
      <div className="report-grid"><label>State<input aria-label="State" value={form.state} onChange={(event) => update("state", event.target.value)} /></label><label>District<input aria-label="District" value={form.district} onChange={(event) => update("district", event.target.value)} /></label><label>City<input aria-label="City" value={form.city} onChange={(event) => update("city", event.target.value)} /></label></div>
      <label>Reporter alias (optional)<input aria-label="Reporter alias" value={form.reporter_alias} onChange={(event) => update("reporter_alias", event.target.value)} /></label>
      <div className="report-grid"><label>Media type<select aria-label="Media type" value={form.media_type} onChange={(event) => update("media_type", event.target.value)}><option value="IMAGE">Image reference</option><option value="VIDEO">Video reference</option></select></label><label>Media reference (optional)<input aria-label="Media reference" placeholder="https:// or demo://" value={form.media_reference} onChange={(event) => update("media_reference", event.target.value)} /></label></div>
      <label>Media caption (optional)<input aria-label="Media caption" value={form.media_caption} onChange={(event) => update("media_caption", event.target.value)} /></label>
      {error ? <p className="error-message" role="alert">{error}</p> : null}
      {mutation.isError ? <p className="error-message" role="alert">The report could not be submitted. Please try again.</p> : null}
      <button type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Submitting…" : "Submit weather report"}</button>
    </form>
  </section>;
}
