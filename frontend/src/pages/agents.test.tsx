import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AgentsPage } from "./agents";
import { renderWithApp } from "../test/render-app";

describe("AgentsPage", () => {
  it("displays approval state in the AI command preview", async () => {
    const user = userEvent.setup();
    renderWithApp(<AgentsPage />);

    await user.click(screen.getByRole("button", { name: /Preview Action/i }));

    expect(await screen.findByTestId("command-preview-state")).toHaveTextContent(/needs approval/i);
    expect(screen.getByText(/Bulk customer actions require approval/i)).toBeInTheDocument();
  });
});
