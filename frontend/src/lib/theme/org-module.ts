/** Resolve which vertical module the current organization uses. */
export type OrgModule = "insurance" | "construction" | "medical-office" | "general";

export function resolveOrgModule(tenantKey?: string | null): OrgModule {
  const key = (tenantKey || "").toLowerCase();
  if (key.includes("insur")) return "insurance";
  if (key.includes("construction")) return "construction";
  if (key.includes("medical")) return "medical-office";
  return "general";
}

export function isInsuranceModule(tenantKey?: string | null): boolean {
  return resolveOrgModule(tenantKey) === "insurance";
}

/** Task domain stored in the database for each vertical module. */
export function taskDomainForModule(module: OrgModule): string {
  if (module === "medical-office") return "medical_office";
  return module;
}
