import { describe, expect, it } from "vitest";

import { buildReminderHistoryListParams } from "./api";

describe("buildReminderHistoryListParams", () => {
  it("maps filters to API query params with 1-based page", () => {
    expect(
      buildReminderHistoryListParams({
        status: "sent",
        channel: "Email",
        dateFrom: "2026-07-01",
        dateTo: "2026-07-15",
        search: "rent",
        page: 2,
        pageSize: 25,
      })
    ).toEqual({
      status: "SENT",
      channel: "email",
      executed_from: "2026-07-01T00:00:00",
      executed_to: "2026-07-15T23:59:59",
      search: "rent",
      page: 3,
      page_size: 25,
    });
  });

  it("omits all/empty filter values", () => {
    expect(
      buildReminderHistoryListParams({
        module: "policy",
        status: "all",
        channel: "all",
        dateFrom: "",
        dateTo: "",
        search: "  ",
        page: 0,
        pageSize: 50,
      })
    ).toEqual({
      status: undefined,
      channel: undefined,
      executed_from: undefined,
      executed_to: undefined,
      search: undefined,
      page: 1,
      page_size: 50,
    });
  });
});
