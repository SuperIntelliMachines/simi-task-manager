import { describe, expect, it } from "vitest";

import { resolveReminderModuleContext } from "./module-context";

describe("resolveReminderModuleContext", () => {
  it("locks Insurance workspace to policy", () => {
    expect(
      resolveReminderModuleContext({
        workspaceId: "insurance",
        pathname: "/app/reminders/create",
      })
    ).toEqual({
      moduleKey: "policy",
      locked: true,
      workspaceId: "insurance",
    });
  });

  it("locks Claims workspace to claims", () => {
    expect(
      resolveReminderModuleContext({
        workspaceId: "claims",
        pathname: "/claims/reminder-management/create",
      })
    ).toEqual({
      moduleKey: "claims",
      locked: true,
      workspaceId: "claims",
    });
  });

  it("locks Inventory workspace to inventory", () => {
    expect(
      resolveReminderModuleContext({
        workspaceId: "inventory",
        pathname: "/app/reminders/create",
      })
    ).toEqual({
      moduleKey: "inventory",
      locked: true,
      workspaceId: "inventory",
    });
  });

  it("uses path hint for inventory routes when workspace is generic", () => {
    expect(
      resolveReminderModuleContext({
        workspaceId: "generic",
        pathname: "/app/inventory/reminders",
      })
    ).toEqual({
      moduleKey: "inventory",
      locked: true,
      workspaceId: "generic",
    });
  });

  it("does not lock global/generic Reminder Management", () => {
    expect(
      resolveReminderModuleContext({
        workspaceId: "generic",
        pathname: "/app/reminders/create",
      })
    ).toEqual({
      moduleKey: null,
      locked: false,
      workspaceId: "generic",
    });
  });
});
