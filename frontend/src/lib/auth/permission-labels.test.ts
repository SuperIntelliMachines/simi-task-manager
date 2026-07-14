import { describe, expect, it } from "vitest";
import {
  formatPermissionActionLabel,
  formatPermissionDisplay,
  formatPermissionModuleLabel,
  groupPermissionsByModule,
  parsePermissionCode,
} from "./permission-labels";

describe("permission-labels", () => {
  it("parses module:action codes", () => {
    expect(parsePermissionCode("admin:create")).toEqual({ module: "admin", action: "create" });
    expect(parsePermissionCode("claims:view")).toEqual({ module: "claims", action: "view" });
  });

  it("formats known modules with friendly labels", () => {
    expect(formatPermissionModuleLabel("admin")).toBe("Administration");
    expect(formatPermissionModuleLabel("claims:view")).toBe("Claims");
    expect(formatPermissionModuleLabel("insurance:update")).toBe("Insurance");
  });

  it("title-cases unknown modules without a registry entry", () => {
    expect(formatPermissionModuleLabel("medical_office")).toBe("Medical Office");
    expect(formatPermissionModuleLabel("hr")).toBe("HR");
    expect(formatPermissionModuleLabel("crm")).toBe("CRM");
  });

  it("formats actions as readable labels", () => {
    expect(formatPermissionActionLabel("create")).toBe("Create");
    expect(formatPermissionActionLabel("process")).toBe("Process");
    expect(formatPermissionActionLabel("insurance:update")).toBe("Update");
  });

  it("returns module + action display pair", () => {
    expect(formatPermissionDisplay("admin:create")).toEqual({
      module: "Administration",
      action: "Create",
    });
  });

  it("groups permissions dynamically by module", () => {
    const groups = groupPermissionsByModule([
      { code: "claims:view", module: "claims" },
      { code: "claims:create", module: "claims" },
      { code: "bms:view", module: "bms" },
      { code: "hr:view", module: "hr" },
    ]);
    expect(groups.map((g) => g.moduleKey)).toEqual(["bms", "claims", "hr"]);
    expect(groups.find((g) => g.moduleKey === "claims")?.permissions.map((p) => p.code)).toEqual([
      "claims:view",
      "claims:create",
    ]);
    expect(groups.find((g) => g.moduleKey === "hr")?.moduleLabel).toBe("HR");
  });
});
