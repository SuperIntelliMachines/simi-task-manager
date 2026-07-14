import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { TasksPage } from "./tasks";
import { renderWithApp } from "../test/render-app";
import { getLastCompletedTaskId, getLastTasksUrl, setMockAuthOrg } from "../test/msw/handlers";

describe("TasksPage", () => {
  it("scopes task queries to the authenticated organization and general module domain", async () => {
    setMockAuthOrg(2);
    renderWithApp(<TasksPage />, { tenant: "General", organizationId: 2 });

    await screen.findByText(/General onboarding checklist/i);
    expect(screen.queryByText(/Renew Ravi policy bundle/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Lead follow-up/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Policy renewal/i)).not.toBeInTheDocument();

    await waitFor(() => {
      const lastUrl = getLastTasksUrl();
      expect(lastUrl?.searchParams.get("organization_id")).toBe("2");
      expect(lastUrl?.searchParams.get("domain")).toBe("general");
    });
  });

  it("does not show general-org tasks when authenticated to a different organization", async () => {
    setMockAuthOrg(1);
    renderWithApp(<TasksPage />, { tenant: "General", organizationId: 1 });

    await waitFor(() => {
      const lastUrl = getLastTasksUrl();
      expect(lastUrl?.searchParams.get("organization_id")).toBe("1");
    });

    expect(screen.queryByText(/General onboarding checklist/i)).not.toBeInTheDocument();
  });

  it("updates task filter query parameters", async () => {
    setMockAuthOrg(2);
    const user = userEvent.setup();
    renderWithApp(<TasksPage />, { tenant: "General", organizationId: 2 });

    await screen.findByText(/General onboarding checklist/i);
    await user.type(screen.getByLabelText(/Assignee filter/i), "Alex");
    await user.selectOptions(screen.getByLabelText(/Priority filter/i), "medium");

    await waitFor(() => {
      const lastUrl = getLastTasksUrl();
      expect(lastUrl?.searchParams.get("organization_id")).toBe("2");
      expect(lastUrl?.searchParams.get("domain")).toBe("general");
      expect(lastUrl?.searchParams.get("assignee")).toBe("Alex");
      expect(lastUrl?.searchParams.get("priority")).toBe("medium");
    });
  });

  it("completes a task and refreshes the cache", async () => {
    setMockAuthOrg(2);
    const user = userEvent.setup();
    renderWithApp(<TasksPage />, { tenant: "General", organizationId: 2 });

    await screen.findByText(/General onboarding checklist/i);
    const actionSelects = screen.getAllByLabelText(/Task actions/i);
    await user.selectOptions(actionSelects[0], "completed");

    await waitFor(() => expect(getLastCompletedTaskId()).toBe(3));
    await waitFor(() => expect(screen.getByText(/^completed$/i, { selector: "span" })).toBeInTheDocument());
  });
});
