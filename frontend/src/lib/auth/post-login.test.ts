import { describe, expect, it } from "vitest";
import { isPlatformAdministrator, resolvePostLoginPath } from "./post-login";

describe("post-login navigation", () => {
  it("routes administrators to the admin console", () => {
    expect(resolvePostLoginPath({ role: "platform_admin", organization_name: "Insurance Co" })).toBe("/master");
    expect(resolvePostLoginPath({ permissions: ["admin:view"], organization_name: "Insurance Co" })).toBe("/master");
  });

  it("routes tenant users to module-specific workspaces", () => {
    expect(resolvePostLoginPath({ role: "org_admin", organization_name: "SIMI Insurance" })).toBe("/app/insurance");
    expect(resolvePostLoginPath({ role: "agent", organization_name: "SIMI Insurance" })).toBe("/app/insurance");
    expect(resolvePostLoginPath({ role: "tenant_user", organization_name: "SIMI Insurance" })).toBe("/app/insurance");
    expect(resolvePostLoginPath({ role: "manager", organization_name: "SIMI Insurance" })).toBe("/app/insurance");
    expect(resolvePostLoginPath({ role: "manager", organization_name: "BuildCo Construction" })).toBe("/app/construction");
    expect(resolvePostLoginPath({ role: "manager", organization_name: "Care Medical Office" })).toBe("/app/medical-office");
    expect(resolvePostLoginPath({ role: "manager", organization_name: "Claims" })).toBe("/claims/dashboard");
    expect(resolvePostLoginPath({ role: "manager", organization_name: "General Org" })).toBe("/app");
  });

  it("does not treat insurance orgs as claims", () => {
    expect(resolvePostLoginPath({ role: "manager", organization_name: "Claims Insurance Co" })).toBe("/app/insurance");
  });

  it("detects platform administrators by role or permission", () => {
    expect(isPlatformAdministrator({ role: "support_engineer" })).toBe(true);
    expect(isPlatformAdministrator({ role: "manager", permissions: ["admin:view"] })).toBe(true);
    expect(isPlatformAdministrator({ role: "manager", permissions: ["tasks:view"] })).toBe(false);
  });
});
