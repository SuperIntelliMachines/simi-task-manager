import { describe, expect, it } from "vitest";
import { ADMIN_WORKSPACE, CLAIMS_WORKSPACE, GENERIC_WORKSPACE, INSURANCE_WORKSPACE } from "./configs";
import { resolveOrgDisplayName, resolveWorkspaceConfig } from "./resolve";

describe("resolveWorkspaceConfig", () => {
  const allowAll = () => true;
  const denyAll = () => false;

  it("resolves Admin Console for /master routes", () => {
    expect(
      resolveWorkspaceConfig({
        pathname: "/master/organizations",
        hasPermission: allowAll,
      }).id,
    ).toBe(ADMIN_WORKSPACE.id);
  });

  it("resolves Claims for claims org or /claims paths", () => {
    expect(
      resolveWorkspaceConfig({
        pathname: "/claims/dashboard",
        organizationName: "Claims",
        hasPermission: allowAll,
      }).id,
    ).toBe(CLAIMS_WORKSPACE.id);
  });

  it("keeps Claims workspace on Reminder Management under /claims", () => {
    expect(
      resolveWorkspaceConfig({
        pathname: "/claims/reminder-management",
        organizationName: "Claims",
        hasPermission: allowAll,
      }).id,
    ).toBe(CLAIMS_WORKSPACE.id);
  });

  it("resolves Insurance when tenant and permission match", () => {
    expect(
      resolveWorkspaceConfig({
        pathname: "/app/insurance",
        tenantKey: "simi-insurance",
        hasPermission: allowAll,
      }).id,
    ).toBe(INSURANCE_WORKSPACE.id);
  });

  it("resolves Insurance from organization name", () => {
    expect(
      resolveWorkspaceConfig({
        pathname: "/app/reminders",
        organizationName: "SIMI Insurance",
        hasPermission: allowAll,
      }).id,
    ).toBe(INSURANCE_WORKSPACE.id);
  });

  it("keeps Insurance workspace on Reminder Management under /app", () => {
    expect(
      resolveWorkspaceConfig({
        pathname: "/app/reminders",
        tenantKey: "simi-insurance",
        hasPermission: allowAll,
      }).id,
    ).toBe(INSURANCE_WORKSPACE.id);
  });

  it("resolves Insurance chrome for deep-linked Insurance routes without permission yet", () => {
    expect(
      resolveWorkspaceConfig({
        pathname: "/app/insurance/policies",
        hasPermission: denyAll,
      }).id,
    ).toBe(INSURANCE_WORKSPACE.id);
  });

  it("does not resolve Insurance without permission on generic /app", () => {
    expect(
      resolveWorkspaceConfig({
        pathname: "/app",
        tenantKey: "simi-insurance",
        hasPermission: denyAll,
      }).id,
    ).not.toBe(INSURANCE_WORKSPACE.id);
  });

  it("falls back to Generic when no module signals match", () => {
    expect(
      resolveWorkspaceConfig({
        pathname: "/app",
        organizationName: "General Org",
        hasPermission: allowAll,
      }).id,
    ).toBe(GENERIC_WORKSPACE.id);
  });
});

describe("resolveOrgDisplayName", () => {
  it("uses Insurance label when workspace is Insurance and names are empty", () => {
    expect(
      resolveOrgDisplayName({
        workspace: INSURANCE_WORKSPACE,
      }),
    ).toBe("Insurance");
  });
});
