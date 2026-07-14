import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useEffect,
  type PropsWithChildren,
} from "react";
import { hasPermission as checkPermission } from "../../lib/auth/permissions";
import type { AuthMeProfile } from "../../lib/auth/post-login";
import { organizationLabelFromProfile } from "../../lib/auth/post-login";
import { LOGIN_PATH } from "../../lib/auth/routes";

export type UserRole = "owner" | "manager" | "staff" | "viewer";

export type CurrentUser = {
  id: number;
  email: string;
};

type WorkbenchContextValue = {
  organizationId: number | null;
  tenantLabel: string;
  tenantKey: string;
  organizationName: string;
  setTenant: (label: string) => void;
  role: UserRole;
  apiRole: string;
  permissions: string[];
  hasPermission: (permission: string) => boolean;
  setRole: (role: UserRole) => void;
  /** @deprecated Prefer `currentUser?.email` */
  currentUserName: string;
  currentUser: CurrentUser | null;
  refreshSession: () => Promise<AuthMeProfile | null>;
  clearSession: () => Promise<void>;
  signOut: () => Promise<void>;
};

const WorkbenchContext = createContext<WorkbenchContextValue | null>(null);

const AUTH_USER_KEY = "atm:currentUserName";
const REFRESH_TOKEN_KEY = "atm:refreshToken";
const PERMISSIONS_KEY = "atm:permissions";
const ORGANIZATION_ID_KEY = "atm:organizationId";

function mapApiRole(role: string | undefined): UserRole {
  const r = (role || "").toLowerCase();
  if (r === "owner") return "owner";
  if (r === "staff") return "staff";
  if (r === "viewer") return "viewer";
  return "manager";
}

function readStoredUser(): CurrentUser | null {
  try {
    const token = localStorage.getItem("atm:token");
    const email = localStorage.getItem(AUTH_USER_KEY);
    if (!token || !email) return null;
    return { id: 0, email };
  } catch {
    return null;
  }
}

function readOrgFromStorage() {
  try {
    const v = localStorage.getItem("atm:organizationName") || "";
    if (!v) return "";
    if (v.toLowerCase().includes("default organization")) return "";
    return v;
  } catch {
    return "";
  }
}

function readTenantLabelFromStorage(): string {
  try {
    const token = localStorage.getItem("atm:token");
    if (!token) return "";
    const tenant = localStorage.getItem("atm:tenant") || "";
    if (tenant) return tenant;
    // Fall back so workspace keys resolve on first paint before effects run.
    return readOrgFromStorage();
  } catch {
    return "";
  }
}

function readOrgIdFromStorage(): number | null {
  try {
    const token = localStorage.getItem("atm:token");
    if (!token) return null;
    const raw = localStorage.getItem(ORGANIZATION_ID_KEY);
    if (!raw) return null;
    const parsed = Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  } catch {
    return null;
  }
}

function mapTenantLabelToKey(label: string) {
  const l = (label || "").toLowerCase();
  if (!l) return "";
  if (l.trim() === "claims") return "claims";
  if (l.includes("insur")) return "insurance";
  if (l.includes("construction")) return "construction";
  if (l.includes("medical")) return "medical-office";
  return l.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export function WorkbenchProvider({
  children,
  initialRole = "manager",
}: PropsWithChildren<{ initialRole?: UserRole }>) {
  const [role, setRole] = useState<UserRole>(initialRole);
  const [organizationId, setOrganizationId] = useState<number | null>(readOrgIdFromStorage);
  const [tenantLabel, setTenantLabel] = useState<string>(readTenantLabelFromStorage);
  const [organizationName, setOrganizationName] = useState<string>(readOrgFromStorage);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(readStoredUser);
  const [apiRole, setApiRole] = useState<string>("");
  const [permissions, setPermissions] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(PERMISSIONS_KEY);
      return raw ? (JSON.parse(raw) as string[]) : [];
    } catch {
      return [];
    }
  });

  const setTenant = useCallback((label: string) => {
    try {
      localStorage.setItem("atm:tenant", label);
    } catch {
      // ignore
    }
    setTenantLabel(label);
  }, []);

  const clearSession = useCallback(async () => {
    const token = localStorage.getItem("atm:token");
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (token) {
      try {
        await fetch("/api/v1/auth/logout", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch {
        // ignore network errors during logout
      }
    }
    try {
      localStorage.removeItem("atm:token");
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      localStorage.removeItem("atm:tenant");
      localStorage.removeItem(AUTH_USER_KEY);
      localStorage.removeItem("atm:organizationName");
      localStorage.removeItem(ORGANIZATION_ID_KEY);
      localStorage.removeItem(PERMISSIONS_KEY);
    } catch {
      // ignore
    }
    setCurrentUser(null);
    setOrganizationId(null);
    setTenantLabel("");
    setOrganizationName("");
    setApiRole("");
    setPermissions([]);
    setRole(initialRole);
  }, [initialRole]);

  const signOut = useCallback(async () => {
    await clearSession();
    window.location.assign(LOGIN_PATH);
  }, [clearSession]);

  const refreshSession = useCallback(async (): Promise<AuthMeProfile | null> => {
    try {
      const token = localStorage.getItem("atm:token");
      if (!token) {
        setCurrentUser(null);
        setOrganizationId(null);
        return null;
      }

      const res = await fetch("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });

      // Only wipe the session on definitive auth failures. Transient 5xx / network
      // blips must not clear organizationId (that caused Insurance dashboards to
      // stick on "Loading organization..." after Reminder Management remounts).
      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          await clearSession();
        }
        return null;
      }

      const data = (await res.json()) as AuthMeProfile & {
        id?: number;
        email?: string;
        organization_id?: number;
      };

      if (data.email) {
        const user: CurrentUser = { id: data.id ?? 0, email: data.email };
        setCurrentUser(user);
        try {
          localStorage.setItem(AUTH_USER_KEY, data.email);
        } catch {
          // ignore
        }
      }

      if (data.role) {
        setApiRole(data.role);
        setRole(mapApiRole(data.role));
      }

      if (data.permissions) {
        setPermissions(data.permissions);
        try {
          localStorage.setItem(PERMISSIONS_KEY, JSON.stringify(data.permissions));
        } catch {
          // ignore
        }
      }

      if (data.organization_id != null && Number(data.organization_id) > 0) {
        const orgId = Number(data.organization_id);
        setOrganizationId(orgId);
        try {
          localStorage.setItem(ORGANIZATION_ID_KEY, String(orgId));
        } catch {
          // ignore
        }
      }

      const rawOrgName = (data.organization_name || "").trim();
      const orgLabel = organizationLabelFromProfile(data);
      // Always keep tenantLabel for workspace key derivation, even when display
      // name is suppressed (e.g. "Default Organization").
      const tenantSource = orgLabel || rawOrgName;
      if (tenantSource) {
        setTenantLabel(tenantSource);
        try {
          localStorage.setItem("atm:tenant", tenantSource);
        } catch {
          // ignore
        }
      }
      if (orgLabel) {
        setOrganizationName(orgLabel);
        try {
          localStorage.setItem("atm:organizationName", orgLabel);
        } catch {
          // ignore
        }
      }

      return data;
    } catch {
      return null;
    }
  }, [clearSession]);

  // Load authenticated user from the active token on mount
  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  // Derive workspace keys from whichever org signal is already available.
  // Prefer tenantLabel, but fall back to organizationName so first paint after
  // reload does not incorrectly resolve Generic before effects run.
  const tenantKey = mapTenantLabelToKey(tenantLabel || organizationName);

  const hasPermission = useCallback(
    (permission: string) => checkPermission(permissions, permission),
    [permissions]
  );

  const value = useMemo<WorkbenchContextValue>(
    () => ({
      organizationId,
      tenantLabel,
      tenantKey,
      organizationName,
      setTenant,
      role,
      apiRole,
      permissions,
      hasPermission,
      setRole,
      currentUser,
      currentUserName: currentUser?.email ?? "",
      refreshSession,
      clearSession,
      signOut,
    }),
    [
      organizationId,
      tenantLabel,
      tenantKey,
      organizationName,
      setTenant,
      role,
      apiRole,
      permissions,
      hasPermission,
      currentUser,
      refreshSession,
      clearSession,
      signOut,
    ]
  );

  return <WorkbenchContext.Provider value={value}>{children}</WorkbenchContext.Provider>;
}

export function useWorkbench() {
  const value = useContext(WorkbenchContext);
  if (!value) {
    throw new Error("useWorkbench must be used within WorkbenchProvider");
  }
  return value;
}
