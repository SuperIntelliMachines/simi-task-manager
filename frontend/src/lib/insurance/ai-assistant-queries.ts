import { apiClient } from "../api/client";
import type { InsuranceDashboard, InsuranceLeadCard, InsurancePolicyCard } from "../api/types";
import { formatPreferredChannelsLabel } from "./custom-reminder-config";
import { getFollowupCustomerName } from "../utils/followup-display";
import { formatDate } from "../utils/formatDate";
import {
  isActivePolicy,
  isDue,
  isGracePeriod,
  isLapsed,
  isExpiring,
  isWithinRenewalWindow,
  sortByNearestExpiry,
} from "../utils/policy-classifier";

export type InsuranceAiQuestionId =
  | "active_policies_count"
  | "total_policies_count"
  | "lapsed_policies"
  | "upcoming_renewals"
  | "expiring_30_days"
  | "pending_followups"
  | "immediate_attention"
  | "policies_by_provider"
  | "total_premium_value"
  | "recently_added_policies"
  | "todays_followups"
  | "renewal_summary";

export type InsuranceAiIntent =
  | "greeting"
  | "small_talk"
  | "unknown"
  | InsuranceAiQuestionId;

export type InsuranceAiProcessResult = {
  intent: InsuranceAiIntent;
  response: string;
  selectableItems?: InsuranceAiSelectableItem[];
};

export type InsuranceAiSelectableItem = {
  kind: "policy";
  id: number;
  policy_number: string;
  policyholder_name: string;
};

export type InsuranceAiQuestionResult = {
  response: string;
  selectableItems?: InsuranceAiSelectableItem[];
};

export const INSURANCE_AI_INVALID_SELECTION_RESPONSE =
  "Invalid selection. Please choose a valid policy number from the list.";

export const INSURANCE_AI_GREETING_RESPONSE =
  "Hello! I'm your Insurance AI Copilot. How can I help you today?";

export const INSURANCE_AI_UNKNOWN_RESPONSE =
  "I didn't understand that. Try asking about policies, renewals, follow-ups, or premiums.";

export const INSURANCE_AI_SMALL_TALK_RESPONSE =
  "I'm here and ready to help with your insurance portfolio. Ask me about active policies, renewals, follow-ups, or premium totals.";

export type InsuranceAiInsight = {
  label: string;
  value: number | string;
};

export type InsuranceAiQuestion = {
  id: InsuranceAiQuestionId;
  label: string;
};

export const INSURANCE_AI_WELCOME_MESSAGE = `Hello! I'm your AI Assistant.

I can help you analyze policies, renewals, follow-ups, and customer insights.`;

export const INSURANCE_AI_QUICK_ACTIONS: InsuranceAiQuestion[] = [
  { id: "active_policies_count", label: "Active Policies" },
  { id: "lapsed_policies", label: "Lapsed Policies" },
  { id: "upcoming_renewals", label: "Renewal Due Soon" },
  { id: "pending_followups", label: "Pending Follow-ups" },
  { id: "immediate_attention", label: "Customers Needing Attention" },
  { id: "total_premium_value", label: "Total Premium Value" },
  { id: "policies_by_provider", label: "Policies by Provider" },
  { id: "recently_added_policies", label: "Recent Policies" },
  { id: "renewal_summary", label: "Renewal Summary" },
];

export const INSURANCE_AI_QUESTIONS: InsuranceAiQuestion[] = [
  { id: "active_policies_count", label: "How many active policies do we have?" },
  { id: "lapsed_policies", label: "Show lapsed policies." },
  { id: "upcoming_renewals", label: "Show upcoming renewals." },
  { id: "expiring_30_days", label: "Show policies expiring in the next 30 days." },
  { id: "pending_followups", label: "Show pending follow-ups." },
  { id: "immediate_attention", label: "Which customers need immediate attention?" },
  { id: "policies_by_provider", label: "Show policies by provider." },
  { id: "total_premium_value", label: "Show total premium value." },
  { id: "recently_added_policies", label: "Show recently added policies." },
  { id: "todays_followups", label: "Show today's follow-up activities." },
  { id: "renewal_summary", label: "Show renewal summary." },
];

const PROMPT_MATCHERS: Array<{ pattern: RegExp; id: InsuranceAiQuestionId }> = [
  { pattern: /\b(total policies?|how many policies?)\b/i, id: "total_policies_count" },
  { pattern: /\b(expired|lapsed)\b/i, id: "lapsed_policies" },
  { pattern: /\b(active policies?|how many active)\b/i, id: "active_policies_count" },
  { pattern: /\b(renewal summary|renewals overview)\b/i, id: "renewal_summary" },
  { pattern: /\b(upcoming renewals?|renewals due)\b/i, id: "upcoming_renewals" },
  { pattern: /\b(expiring in (?:the )?(?:next )?30 days|next 30 days)\b/i, id: "expiring_30_days" },
  { pattern: /\b(pending follow[- ]?ups?)\b/i, id: "pending_followups" },
  { pattern: /\b(today'?s follow[- ]?ups?|follow[- ]?ups? today)\b/i, id: "todays_followups" },
  { pattern: /\b(immediate attention|need attention|urgent customers?)\b/i, id: "immediate_attention" },
  { pattern: /\b(policies by provider|by provider|policy provider)\b/i, id: "policies_by_provider" },
  { pattern: /\b(total premium|premium totals?|premium value)\b/i, id: "total_premium_value" },
  { pattern: /\b(recent policies?|recently added)\b/i, id: "recently_added_policies" },
];

function normalizePrompt(prompt: string): string {
  return prompt
    .trim()
    .toLowerCase()
    .replace(/[^\w\s'-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isGreeting(normalized: string): boolean {
  return /^(hi|hello|hey|good morning|good afternoon|good evening)( there)?[!.?]*$/.test(normalized);
}

function isSmallTalk(normalized: string): boolean {
  return /\b(how are you|how'?s it going|what'?s up|how do you do)\b/.test(normalized);
}

export function detectInsuranceAiIntent(
  prompt: string,
  forcedQuestionId?: InsuranceAiQuestionId,
): InsuranceAiIntent {
  if (forcedQuestionId) {
    return forcedQuestionId;
  }

  const normalized = normalizePrompt(prompt);
  if (!normalized) return "unknown";
  if (isGreeting(normalized)) return "greeting";
  if (isSmallTalk(normalized)) return "small_talk";

  for (const action of INSURANCE_AI_QUICK_ACTIONS) {
    const label = action.label.toLowerCase();
    if (normalized === label || normalized.includes(label)) {
      return action.id;
    }
  }

  for (const question of INSURANCE_AI_QUESTIONS) {
    const label = question.label.toLowerCase().replace(/\.$/, "");
    if (normalized === label || normalized.includes(label)) {
      return question.id;
    }
  }

  for (const matcher of PROMPT_MATCHERS) {
    if (matcher.pattern.test(normalized)) {
      return matcher.id;
    }
  }

  return "unknown";
}

export function resolveQuestionFromPrompt(prompt: string): InsuranceAiQuestionId | null {
  const intent = detectInsuranceAiIntent(prompt);
  if (intent === "greeting" || intent === "small_talk" || intent === "unknown") {
    return null;
  }
  return intent;
}

export async function processInsuranceAiMessage(
  organizationId: number,
  prompt: string,
  forcedQuestionId?: InsuranceAiQuestionId,
): Promise<InsuranceAiProcessResult> {
  const intent = detectInsuranceAiIntent(prompt, forcedQuestionId);
  let response: string;
  let selectableItems: InsuranceAiSelectableItem[] | undefined;

  if (intent === "greeting") {
    response = INSURANCE_AI_GREETING_RESPONSE;
  } else if (intent === "small_talk") {
    response = INSURANCE_AI_SMALL_TALK_RESPONSE;
  } else if (intent === "unknown") {
    response = INSURANCE_AI_UNKNOWN_RESPONSE;
  } else {
    const result = await runInsuranceAiQuestion(organizationId, intent);
    response = result.response;
    selectableItems = result.selectableItems;
  }

  console.info("[Insurance AI Assistant]", {
    userQuestion: prompt,
    intentDetected: intent,
    generatedResponse: response,
    selectableCount: selectableItems?.length ?? 0,
  });

  return { intent, response, selectableItems };
}

export function isNumericListSelection(prompt: string): boolean {
  return /^\d+$/.test(prompt.trim());
}

export function resolveListSelectionIndex(prompt: string): number | null {
  const trimmed = prompt.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const index = Number.parseInt(trimmed, 10);
  return Number.isFinite(index) && index > 0 ? index : null;
}

export async function processInsuranceAiListSelection(
  items: InsuranceAiSelectableItem[],
  prompt: string,
): Promise<InsuranceAiProcessResult> {
  const index = resolveListSelectionIndex(prompt);
  const item = index != null ? items[index - 1] : undefined;

  if (!item || item.kind !== "policy") {
    return {
      intent: "unknown",
      response: INSURANCE_AI_INVALID_SELECTION_RESPONSE,
    };
  }

  const response = await fetchInsuranceAiPolicyDetails(item.id);
  return {
    intent: "unknown",
    response,
  };
}

export async function fetchInsuranceAiPolicyDetails(policyId: number): Promise<string> {
  const policy = await apiClient.getPolicy(policyId);
  if (!policy) {
    return "Could not load policy details. Please try again.";
  }
  return formatPolicyDetailsForAiChat(policy);
}

export function formatPolicyDetailsForAiChat(policy: InsurancePolicyCard): string {
  const status = (policy.status || "unknown").replace(/_/g, " ");
  const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);

  return [
    "Policy details:",
    "",
    `Policy Number: ${policy.policy_number || "-"}`,
    `Customer Name: ${policy.policyholder_name || "-"}`,
    `Provider: ${policy.carrier?.trim() || "-"}`,
    `Policy Type: ${policy.policy_type?.trim() || "-"}`,
    `Renewal Date: ${formatDate(policy.expiry_date) || "-"}`,
    `Premium Amount: ${formatCurrencyInr(parsePremiumValue(policy.premium))}`,
    `Policy Status: ${statusLabel}`,
    `Preferred Channel: ${formatPreferredChannelsLabel(policy.preferred_channel)}`,
  ].join("\n");
}

type InsuranceAiData = {
  dashboard: InsuranceDashboard;
  policies: InsurancePolicyCard[];
  followups: InsuranceLeadCard[];
};

function isPendingFollowup(item: InsuranceLeadCard): boolean {
  const decision = (item as { customer_decision?: string }).customer_decision;
  return item.status === "follow_up_pending" || decision === "Pending";
}

function formatPolicyLine(index: number, policy: InsurancePolicyCard): string {
  return `${index}. ${policy.policy_number} - ${policy.policyholder_name}`;
}

function toSelectablePolicies(policies: InsurancePolicyCard[]): InsuranceAiSelectableItem[] {
  return policies.map((policy) => ({
    kind: "policy",
    id: policy.id,
    policy_number: policy.policy_number,
    policyholder_name: policy.policyholder_name,
  }));
}

function formatPolicyList(intro: string, policies: InsurancePolicyCard[], emptyMessage: string): string {
  if (policies.length === 0) return emptyMessage;
  const lines = policies.map((policy, index) => formatPolicyLine(index + 1, policy)).join("\n");
  return `${intro}\n\n${lines}`;
}

function buildPolicyListResult(
  intro: string,
  policies: InsurancePolicyCard[],
  emptyMessage: string,
): InsuranceAiQuestionResult {
  if (policies.length === 0) {
    return { response: emptyMessage };
  }
  return {
    response: formatPolicyList(intro, policies, emptyMessage),
    selectableItems: toSelectablePolicies(policies),
  };
}

function parsePremiumValue(value: InsurancePolicyCard["premium"]): number {
  if (value == null || value === "") return 0;
  const parsed = typeof value === "number" ? value : Number.parseFloat(String(value));
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatCurrencyInr(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

function isFollowupDueToday(followup: InsuranceLeadCard): boolean {
  const dueAt = followup.followup_due_at;
  if (!dueAt) return false;
  const due = new Date(dueAt);
  if (Number.isNaN(due.getTime())) return false;
  const now = new Date();
  return (
    due.getUTCFullYear() === now.getUTCFullYear() &&
    due.getUTCMonth() === now.getUTCMonth() &&
    due.getUTCDate() === now.getUTCDate()
  );
}

function isFollowupOverdue(followup: InsuranceLeadCard): boolean {
  const dueAt = followup.followup_due_at;
  if (!dueAt) return false;
  const due = new Date(dueAt);
  if (Number.isNaN(due.getTime())) return false;
  const now = new Date();
  const dueDay = Date.UTC(due.getUTCFullYear(), due.getUTCMonth(), due.getUTCDate());
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return dueDay < today;
}

async function loadInsuranceAiData(organizationId: number): Promise<InsuranceAiData> {
  const [dashboard, policies, followups] = await Promise.all([
    apiClient.insuranceDashboard(organizationId),
    apiClient.listPolicies(organizationId),
    apiClient.listFollowups(organizationId),
  ]);

  return { dashboard, policies, followups };
}

export async function fetchInsuranceAiInsights(organizationId: number): Promise<InsuranceAiInsight[]> {
  const { dashboard, policies, followups } = await loadInsuranceAiData(organizationId);
  const activePolicies =
    typeof dashboard.counts?.active_policies === "number"
      ? dashboard.counts.active_policies
      : policies.filter(isActivePolicy).length;
  const upcomingRenewals = policies.filter(isWithinRenewalWindow).length;
  const pendingFollowups = followups.filter(isPendingFollowup).length;

  return [
    { label: "Total Policies", value: policies.length },
    { label: "Active Policies", value: activePolicies },
    {
      label: "Grace Period",
      value: dashboard.counts?.grace_period_policies ?? policies.filter(isGracePeriod).length,
    },
    { label: "Lapsed", value: dashboard.counts?.lapsed_policies ?? policies.filter(isLapsed).length },
    { label: "Renewal Due Soon", value: upcomingRenewals },
    { label: "Pending Follow-ups", value: dashboard.counts?.pending_followups ?? pendingFollowups },
  ];
}

export async function runInsuranceAiQuestion(
  organizationId: number,
  questionId: InsuranceAiQuestionId,
): Promise<InsuranceAiQuestionResult> {
  const { dashboard, policies, followups } = await loadInsuranceAiData(organizationId);

  switch (questionId) {
    case "total_policies_count": {
      return {
        response: `We currently have ${policies.length} total ${policies.length === 1 ? "policy" : "policies"}.`,
      };
    }

    case "active_policies_count": {
      const activeCount =
        typeof dashboard.counts?.active_policies === "number"
          ? dashboard.counts.active_policies
          : policies.filter(isActivePolicy).length;
      return {
        response: `We currently have ${activeCount} active ${activeCount === 1 ? "policy" : "policies"}.`,
      };
    }

    case "lapsed_policies": {
      const lapsed = sortByNearestExpiry(
        policies.filter((policy) => isLapsed(policy) || (policy.status || "").toLowerCase() === "lapsed"),
      );
      return buildPolicyListResult(
        `We currently have ${lapsed.length} lapsed ${lapsed.length === 1 ? "policy" : "policies"}:`,
        lapsed,
        "There are no lapsed policies right now.",
      );
    }

    case "upcoming_renewals": {
      const renewals = sortByNearestExpiry(policies.filter(isWithinRenewalWindow));
      return buildPolicyListResult(
        `We currently have ${renewals.length} upcoming ${renewals.length === 1 ? "renewal" : "renewals"}:`,
        renewals,
        "There are no upcoming renewals in the next 10 days.",
      );
    }

    case "expiring_30_days": {
      const expiring = sortByNearestExpiry(policies.filter(isWithinRenewalWindow));
      return buildPolicyListResult(
        `${expiring.length} ${expiring.length === 1 ? "policy expires" : "policies expire"} in the next 30 days:`,
        expiring,
        "No policies are expiring in the next 30 days.",
      );
    }

    case "pending_followups": {
      const pending = followups.filter(isPendingFollowup);
      if (pending.length === 0) {
        return { response: "There are no pending follow-ups right now." };
      }
      const lines = pending
        .map((item, index) => {
          const name = getFollowupCustomerName(item);
          const due = item.followup_due_at ? formatDate(item.followup_due_at) : "No date";
          return `${index + 1}. ${name} - due ${due}`;
        })
        .join("\n");
      return { response: `We currently have ${pending.length} pending follow-ups:\n\n${lines}` };
    }

    case "immediate_attention": {
      const urgentPolicies = sortByNearestExpiry(
        policies.filter((policy) => isLapsed(policy) || isGracePeriod(policy) || isExpiring(policy, 2) || isDue(policy)),
      );
      const overdueFollowups = followups.filter((item) => isPendingFollowup(item) && isFollowupOverdue(item));

      if (urgentPolicies.length === 0 && overdueFollowups.length === 0) {
        return { response: "No customers need immediate attention right now." };
      }

      const sections: string[] = ["Customers needing immediate attention:"];

      if (urgentPolicies.length > 0) {
        sections.push(
          "",
          `Policies (${urgentPolicies.length}):`,
          ...urgentPolicies.map((policy, index) => formatPolicyLine(index + 1, policy)),
        );
      }

      if (overdueFollowups.length > 0) {
        sections.push(
          "",
          `Overdue follow-ups (${overdueFollowups.length}):`,
          ...overdueFollowups.map((item, index) => {
            const name = getFollowupCustomerName(item);
            const due = item.followup_due_at ? formatDate(item.followup_due_at) : "No date";
            return `${index + 1}. ${name} - overdue since ${due}`;
          }),
        );
      }

      return {
        response: sections.join("\n"),
        selectableItems: urgentPolicies.length > 0 ? toSelectablePolicies(urgentPolicies) : undefined,
      };
    }

    case "policies_by_provider": {
      const counts = new Map<string, number>();
      for (const policy of policies) {
        const provider = (policy.carrier || "Unspecified").trim() || "Unspecified";
        counts.set(provider, (counts.get(provider) ?? 0) + 1);
      }

      if (counts.size === 0) {
        return { response: "No policy provider data is available yet." };
      }

      const lines = [...counts.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .map(([provider, count], index) => `${index + 1}. ${provider}: ${count}`);

      return { response: `Policies by provider:\n\n${lines.join("\n")}` };
    }

    case "total_premium_value": {
      const total = policies.reduce((sum, policy) => sum + parsePremiumValue(policy.premium), 0);
      return {
        response: `Total premium value across ${policies.length} ${policies.length === 1 ? "policy" : "policies"}: ${formatCurrencyInr(total)}.`,
      };
    }

    case "recently_added_policies": {
      const recent = [...policies]
        .sort((a, b) => {
          const aCreated = a.created_at ? new Date(a.created_at).getTime() : a.id;
          const bCreated = b.created_at ? new Date(b.created_at).getTime() : b.id;
          return bCreated - aCreated;
        })
        .slice(0, 10);

      return buildPolicyListResult(
        `Here are the ${recent.length} most recently added ${recent.length === 1 ? "policy" : "policies"}:`,
        recent,
        "No policies have been added yet.",
      );
    }

    case "todays_followups": {
      const todays = followups.filter(isFollowupDueToday);
      if (todays.length === 0) {
        return { response: "There are no follow-up activities scheduled for today." };
      }

      const lines = todays
        .map((item, index) => {
          const name = getFollowupCustomerName(item);
          const status = item.status.replace(/_/g, " ");
          return `${index + 1}. ${name} - ${status}`;
        })
        .join("\n");

      return { response: `Today's follow-up activities (${todays.length}):\n\n${lines}` };
    }

    case "renewal_summary": {
      const inWindow = sortByNearestExpiry(policies.filter(isWithinRenewalWindow));
      const critical = inWindow.filter((policy) => isExpiring(policy, 2));
      const dueSoon = inWindow.filter((policy) => isDue(policy));
      const nearest = inWindow.slice(0, 5);

      const lines = [
        "Renewal summary for the next 10 days:",
        "",
        `• Expiring (0–2 days): ${critical.length}`,
        `• Due renewals (3–10 days): ${dueSoon.length}`,
        `• Total in renewal window: ${inWindow.length}`,
      ];

      if (nearest.length > 0) {
        lines.push("", "Nearest renewals:");
        nearest.forEach((policy, index) => {
          lines.push(formatPolicyLine(index + 1, policy));
        });
      }

      return {
        response: lines.join("\n"),
        selectableItems: nearest.length > 0 ? toSelectablePolicies(nearest) : undefined,
      };
    }

    default:
      return { response: "Sorry, I couldn't process that question." };
  }
}
