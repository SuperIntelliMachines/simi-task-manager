import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { QueryClientProvider } from "./providers/query-client-provider";
import { WorkbenchProvider } from "./providers/workbench-provider";
import { HomePage } from "../pages/home";

describe("HomePage", () => {
  it("renders workbench headline", () => {
    render(
      <QueryClientProvider>
        <WorkbenchProvider>
          <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <HomePage />
          </MemoryRouter>
        </WorkbenchProvider>
      </QueryClientProvider>
    );
    expect(screen.getByText(/Frontend workbench for tasks, agents, channels, and vertical operations/i)).toBeInTheDocument();
  });
});
