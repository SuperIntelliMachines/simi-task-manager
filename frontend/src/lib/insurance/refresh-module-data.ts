import type { QueryClient } from "@tanstack/react-query";

import { fetchInsuranceAiInsights } from "./ai-assistant-queries";

const INSURANCE_QUERY_ROOTS = new Set([
  "insurance-dashboard",
  "insurance-policies",
  "insurance-policy",
  "insurance-followups",
  "insurance-followup",
  "insurance-ai-insights",
]);

function isInsuranceQuery(queryKey: readonly unknown[]): boolean {
  const root = queryKey[0];
  return typeof root === "string" && INSURANCE_QUERY_ROOTS.has(root);
}

export async function refreshInsuranceModuleData(
  queryClient: QueryClient,
  organizationId: number,
): Promise<void> {
  console.info("[Insurance Refresh] Starting data refresh", { organizationId });

  const refetchPromise = queryClient.refetchQueries({
    predicate: (query) => isInsuranceQuery(query.queryKey),
    type: "active",
  });

  const aiInsightsPromise = fetchInsuranceAiInsights(organizationId)
    .then((insights) => {
      queryClient.setQueryData(["insurance-ai-insights", organizationId], insights);
      console.info("[Insurance Refresh] AI insights refreshed", {
        organizationId,
        insightCount: insights.length,
      });
    })
    .catch((error) => {
      console.error("[Insurance Refresh] Failed to refresh AI insights", error);
      throw error;
    });

  await Promise.all([refetchPromise, aiInsightsPromise]);

  window.dispatchEvent(
    new CustomEvent("insurance:data-refreshed", {
      detail: { organizationId },
    }),
  );

  console.info("[Insurance Refresh] Completed data refresh", { organizationId });
}
