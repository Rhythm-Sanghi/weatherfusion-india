import { fireEvent, render, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { EventMap } from "../src/components/EventMap";

vi.mock("maplibre-gl", () => ({
  default: {
    Map: class { addControl() { return this; } on() { return this; } remove() {} },
    Marker: class { setLngLat() { return this; } setPopup() { return this; } addTo() { return this; } },
    Popup: class { setText() { return this; } },
    NavigationControl: class {},
  },
}));

afterEach(() => {
  document.querySelector('script[data-mappls-sdk="true"]')?.remove();
  vi.unstubAllEnvs();
});

test("retries Mappls loading after a failed script request", async () => {
  vi.stubEnv("VITE_MAPPLS_ACCESS_TOKEN", "test-token");
  const first = render(<EventMap events={[]} />);
  const firstScript = await waitFor(() => {
    const script = document.querySelector<HTMLScriptElement>('script[data-mappls-sdk="true"]');
    expect(script).not.toBeNull();
    return script as HTMLScriptElement;
  });
  fireEvent.error(firstScript);
  await waitFor(() => expect(document.querySelector('script[data-mappls-sdk="true"]')).toBeNull());
  first.unmount();

  render(<EventMap events={[]} />);
  await waitFor(() => expect(document.querySelector('script[data-mappls-sdk="true"]')).not.toBeNull());
});
