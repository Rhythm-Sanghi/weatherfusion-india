import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AppShell } from "../src/components/AppShell";

test("renders the WeatherFusion application shell", () => {
  render(
    <MemoryRouter>
      <AppShell />
    </MemoryRouter>,
  );

  expect(screen.getByText("WeatherFusion India")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "System" })).toBeInTheDocument();
});
