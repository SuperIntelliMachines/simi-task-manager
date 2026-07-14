import { describe, expect, it, vi } from "vitest";
import type { QueryClient } from "@tanstack/react-query";

import { refreshInsuranceModuleData } from "./refresh-module-data";

vi.mock("./ai-assistant-queries", () => ({
  fetchInsuranceAiInsights: vi.fn().mockResolvedValue([
    { label: "Total Policies", value: 3 },
  ]),
}));

import { fetchInsuranceAiInsights } from "./ai-assistant-queries";

describe("refreshInsuranceModuleData", () => {
  it("refetches insurance queries and caches AI insights", async () => {
    const refetchQueries = vi.fn().mockResolvedValue(undefined);
    const setQueryData = vi.fn();
    const queryClient = {
      refetchQueries,
      setQueryData,
    } as unknown as QueryClient;

    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    await refreshInsuranceModuleData(queryClient, 42);

    expect(refetchQueries).toHaveBeenCalled();
    expect(fetchInsuranceAiInsights).toHaveBeenCalledWith(42);
    expect(setQueryData).toHaveBeenCalledWith(["insurance-ai-insights", 42], [
      { label: "Total Policies", value: 3 },
    ]);
    expect(dispatchSpy).toHaveBeenCalled();

    dispatchSpy.mockRestore();
  });
});
