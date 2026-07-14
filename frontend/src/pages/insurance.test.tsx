import { screen } from "@testing-library/react";

import { InsurancePage } from "./insurance";
import { renderWithApp } from "../test/render-app";
import { setInsuranceDashboardMode } from "../test/msw/handlers";

describe("InsurancePage", () => {
  it("handles loading and populated states", async () => {
    setInsuranceDashboardMode("loading");
    renderWithApp(<InsurancePage />);

    expect(screen.getByText(/Loading insurance dashboard/i)).toBeInTheDocument();
    expect(await screen.findByText(/Welcome back,/i)).toBeInTheDocument();
    expect(await screen.findByText("Policy Summary")).toBeInTheDocument();
    expect(await screen.findByText("Lead Follow-up Overview")).toBeInTheDocument();
    expect(await screen.findByText("Renewal Intelligence")).toBeInTheDocument();
  });

  it("handles empty state", async () => {
    setInsuranceDashboardMode("empty");
    renderWithApp(<InsurancePage />);

    expect(await screen.findByText(/No insurance activity yet/i)).toBeInTheDocument();
  });
});
