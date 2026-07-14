import { screen } from "@testing-library/react";

import { MedicalOfficePage } from "./medical-office";
import { renderWithApp } from "../test/render-app";

describe("MedicalOfficePage", () => {
  it("redacts sensitive fields for viewer role", async () => {
    renderWithApp(<MedicalOfficePage />, { role: "viewer" });

    expect(await screen.findAllByText("[REDACTED]")).not.toHaveLength(0);
    expect(screen.queryByText(/Elena Morris/i)).not.toBeInTheDocument();
  });
});
