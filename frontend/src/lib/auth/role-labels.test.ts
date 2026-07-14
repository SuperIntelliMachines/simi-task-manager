import { describe, expect, it } from "vitest";
import { ADMIN_CONSOLE_NAME, formatRoleDisplayLabel } from "./role-labels";

describe("formatRoleDisplayLabel", () => {
  it("maps known RBAC role identifiers to display labels", () => {
    expect(formatRoleDisplayLabel("platform_admin")).toBe("Admin");
    expect(formatRoleDisplayLabel("org_admin")).toBe("Organization Admin");
    expect(formatRoleDisplayLabel("manager")).toBe("Manager");
    expect(formatRoleDisplayLabel("agent")).toBe("Agent");
    expect(formatRoleDisplayLabel("viewer")).toBe("Viewer");
    expect(formatRoleDisplayLabel("tenant_user")).toBe("User");
  });

  it("title-cases unknown role identifiers without changing the source value", () => {
    expect(formatRoleDisplayLabel("support_engineer")).toBe("Support Engineer");
  });
});

describe("admin console labels", () => {
  it("uses Admin Console terminology", () => {
    expect(ADMIN_CONSOLE_NAME).toBe("Admin Console");
  });
});
