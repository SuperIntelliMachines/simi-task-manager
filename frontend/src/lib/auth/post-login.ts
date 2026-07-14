export type AuthMeProfile = {
  organization_name?: string | null;
  role?: string | null;
  permissions?: string[];
};

const PLATFORM_ROLES = new Set(["platform_admin", "support_engineer", "implementation_manager"]);

export function isPlatformAdministrator(profile: AuthMeProfile): boolean {
  const role = (profile.role || "").toLowerCase();
  if (PLATFORM_ROLES.has(role)) return true;
  return Boolean(profile.permissions?.includes("admin:view"));
}

/** Exact Claims organization workspace (does not match Insurance/other orgs). */
export function isClaimsOrganization(organizationName?: string | null): boolean {
  return (organizationName || "").trim().toLowerCase() === "claims";
}

export function resolvePostLoginPath(profile: AuthMeProfile): string {
  if (isPlatformAdministrator(profile)) {
    return "/master";
  }

  const orgName = (profile.organization_name || "").toLowerCase();
  if (isClaimsOrganization(profile.organization_name)) return "/claims/dashboard";
  if (orgName.includes("insur")) return "/app/insurance";
  if (orgName.includes("construction")) return "/app/construction";
  if (orgName.includes("medical")) return "/app/medical-office";
  return "/app";
}

export function organizationLabelFromProfile(profile: AuthMeProfile): string | null {
  const name = profile.organization_name?.trim();
  if (!name || name.toLowerCase().includes("default organization")) {
    return null;
  }
  return name;
}
