import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  detectInsuranceAiIntent,
  formatPolicyDetailsForAiChat,
  INSURANCE_AI_GREETING_RESPONSE,
  INSURANCE_AI_INVALID_SELECTION_RESPONSE,
  INSURANCE_AI_UNKNOWN_RESPONSE,
  isNumericListSelection,
  processInsuranceAiListSelection,
  processInsuranceAiMessage,
  runInsuranceAiQuestion,
} from "./ai-assistant-queries";

vi.mock("../api/client", () => ({
  apiClient: {
    insuranceDashboard: vi.fn(),
    listPolicies: vi.fn(),
    listFollowups: vi.fn(),
    getPolicy: vi.fn(),
  },
}));

import { apiClient } from "../api/client";

const mockedDashboard = vi.mocked(apiClient.insuranceDashboard);
const mockedPolicies = vi.mocked(apiClient.listPolicies);
const mockedFollowups = vi.mocked(apiClient.listFollowups);
const mockedGetPolicy = vi.mocked(apiClient.getPolicy);

describe("ai-assistant-queries", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedDashboard.mockResolvedValue({
      due_renewals: [],
      expiring_policies: [],
      grace_period_policies: [],
      lapsed_policies: [],
      pending_followups: [],
      counts: {
        active_policies: 2,
        grace_period_policies: 0,
        lapsed_policies: 1,
        due_renewals: 0,
        pending_followups: 0,
      },
      conversion_metrics: { demo_to_policy_rate: 0, renewal_rate: 0 },
    });
    mockedFollowups.mockResolvedValue([]);
  });

  it("returns active policy count from live data", async () => {
    mockedPolicies.mockResolvedValue([
      {
        id: 1,
        policy_number: "POL-1",
        policyholder_name: "John",
        policy_type: "Health",
        expiry_date: "2030-01-01T00:00:00",
        preferred_channel: null,
        status: "active",
      },
      {
        id: 2,
        policy_number: "POL-2",
        policyholder_name: "Jane",
        policy_type: "Life",
        expiry_date: "2030-02-01T00:00:00",
        preferred_channel: null,
        status: "active",
      },
    ]);

    const { response } = await runInsuranceAiQuestion(1, "active_policies_count");
    expect(response).toBe("We currently have 2 active policies.");
  });

  it("lists lapsed policies from live records with selectable items", async () => {
    mockedPolicies.mockResolvedValue([
      {
        id: 3,
        policy_number: "POL-1997",
        policyholder_name: "Uday",
        policy_type: "Health",
        expiry_date: "2020-01-01T00:00:00",
        preferred_channel: null,
        status: "active",
      },
      {
        id: 4,
        policy_number: "POL-2001",
        policyholder_name: "Ramesh",
        policy_type: "Auto",
        expiry_date: "2019-06-01T00:00:00",
        preferred_channel: null,
        status: "lapsed",
      },
    ]);

    const { response, selectableItems } = await runInsuranceAiQuestion(1, "lapsed_policies");
    expect(response).toContain("We currently have 2 lapsed policies:");
    expect(response).toContain("POL-1997 - Uday");
    expect(response).toContain("POL-2001 - Ramesh");
    expect(selectableItems).toEqual([
      { kind: "policy", id: 4, policy_number: "POL-2001", policyholder_name: "Ramesh" },
      { kind: "policy", id: 3, policy_number: "POL-1997", policyholder_name: "Uday" },
    ]);
  });

  it("detects greetings, insurance queries, and unknown prompts", () => {
    expect(detectInsuranceAiIntent("hi")).toBe("greeting");
    expect(detectInsuranceAiIntent("hello")).toBe("greeting");
    expect(detectInsuranceAiIntent("good morning")).toBe("greeting");
    expect(detectInsuranceAiIntent("how are you?")).toBe("small_talk");
    expect(detectInsuranceAiIntent("show lapsed policies")).toBe("lapsed_policies");
    expect(detectInsuranceAiIntent("total policies")).toBe("total_policies_count");
    expect(detectInsuranceAiIntent("random question")).toBe("unknown");
  });

  it("processes messages with distinct responses", async () => {
    mockedPolicies.mockResolvedValue([
      {
        id: 3,
        policy_number: "POL-1997",
        policyholder_name: "Uday",
        policy_type: "Health",
        expiry_date: "2020-01-01T00:00:00",
        preferred_channel: null,
        status: "active",
      },
    ]);

    const greeting = await processInsuranceAiMessage(1, "hi");
    const unknown = await processInsuranceAiMessage(1, "tell me a joke");
    const lapsed = await processInsuranceAiMessage(1, "show lapsed policies");

    expect(greeting.response).toBe(INSURANCE_AI_GREETING_RESPONSE);
    expect(unknown.response).toBe(INSURANCE_AI_UNKNOWN_RESPONSE);
    expect(lapsed.response).toContain("POL-1997 - Uday");
    expect(lapsed.selectableItems).toHaveLength(1);
    expect(greeting.response).not.toBe(lapsed.response);
  });

  it("identifies numeric list selections", () => {
    expect(isNumericListSelection("1")).toBe(true);
    expect(isNumericListSelection(" 2 ")).toBe(true);
    expect(isNumericListSelection("show 1")).toBe(false);
    expect(isNumericListSelection("hello")).toBe(false);
  });

  it("returns invalid selection for out-of-range numeric input", async () => {
    const items = [{ kind: "policy" as const, id: 3, policy_number: "POL-1", policyholder_name: "Uday" }];
    const result = await processInsuranceAiListSelection(items, "2");
    expect(result.response).toBe(INSURANCE_AI_INVALID_SELECTION_RESPONSE);
  });

  it("fetches policy details for a valid numeric selection", async () => {
    mockedGetPolicy.mockResolvedValue({
      id: 3,
      policy_number: "POL-1997",
      policyholder_name: "Uday",
      policy_type: "Health",
      carrier: "HDFC ERGO",
      premium: 12500,
      expiry_date: "2020-01-01T00:00:00",
      preferred_channel: ["whatsapp"],
      status: "active",
    });

    const items = [{ kind: "policy" as const, id: 3, policy_number: "POL-1997", policyholder_name: "Uday" }];
    const result = await processInsuranceAiListSelection(items, "1");

    expect(mockedGetPolicy).toHaveBeenCalledWith(3);
    expect(result.response).toContain("Policy Number: POL-1997");
    expect(result.response).toContain("Customer Name: Uday");
    expect(result.response).toContain("Provider: HDFC ERGO");
    expect(result.response).toContain("Policy Type: Health");
    expect(result.response).toContain("Premium Amount:");
    expect(result.response).toContain("Preferred Channel:");
  });

  it("formats policy details for chat display", () => {
    const details = formatPolicyDetailsForAiChat({
      id: 1,
      policy_number: "POL-1",
      policyholder_name: "Jane",
      policy_type: "Life",
      carrier: "LIC",
      premium: 5000,
      expiry_date: "2030-06-15T00:00:00",
      preferred_channel: ["email", "sms"],
      status: "lapsed",
    });

    expect(details).toContain("Policy Number: POL-1");
    expect(details).toContain("Customer Name: Jane");
    expect(details).toContain("Provider: LIC");
    expect(details).toContain("Policy Status: Expired");
  });
});
