import type { PropsWithChildren, ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { WorkbenchProvider, type UserRole } from "../app/providers/workbench-provider";
import { ToastProvider } from "../components/ui/toast";
import { setMockAuthOrg } from "./msw/handlers";

export function renderWithApp(
  ui: ReactElement,
  {
    route = "/",
    role = "manager" as UserRole,
    tenant = "General",
    organizationId,
  }: { route?: string; role?: UserRole; tenant?: string; organizationId?: number } = {}
) {
  try {
    localStorage.setItem("atm:token", "test-token");
    localStorage.setItem("atm:currentUserName", "test@example.com");
    localStorage.setItem("atm:tenant", tenant);
  } catch {
    // ignore
  }

  if (organizationId != null) {
    setMockAuthOrg(organizationId);
    try {
      localStorage.setItem("atm:organizationId", String(organizationId));
    } catch {
      // ignore
    }
  } else {
    // Match MSW default mockAuthOrgId so Insurance pages do not hang on
    // "Loading organization..." before /auth/me resolves.
    try {
      localStorage.setItem("atm:organizationId", "2");
    } catch {
      // ignore
    }
  }

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false },
    },
  });

  function Wrapper({ children }: PropsWithChildren) {
    return (
      <QueryClientProvider client={queryClient}>
        <WorkbenchProvider initialRole={role}>
          <ToastProvider>
            <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
              {children}
            </MemoryRouter>
          </ToastProvider>
        </WorkbenchProvider>
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper });
}
