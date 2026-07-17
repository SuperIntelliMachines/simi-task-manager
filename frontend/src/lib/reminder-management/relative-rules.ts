import type {
  RelativeReminderOffsetDirection,
  RelativeReminderOffsetUnit,
  RelativeReminderRule,
} from "../personal-reminders/types";

/** Browser-safe client id for relative rule rows (not persisted). */
export function createRelativeReminderRuleId(): string {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `rule-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function createRelativeReminderRule(
  defaults?: Partial<Omit<RelativeReminderRule, "id">> & { id?: string }
): RelativeReminderRule {
  return {
    id: defaults?.id ?? createRelativeReminderRuleId(),
    offsetValue: defaults?.offsetValue ?? 24,
    offsetUnit: defaults?.offsetUnit ?? "hours",
    offsetDirection: defaults?.offsetDirection ?? "before",
  };
}

export function relativeRuleKey(rule: Pick<
  RelativeReminderRule,
  "offsetValue" | "offsetUnit" | "offsetDirection"
>): string {
  return `${rule.offsetValue}:${rule.offsetUnit}:${rule.offsetDirection}`;
}

export function formatRelativeReminderRuleLabel(
  rule: Pick<RelativeReminderRule, "offsetValue" | "offsetUnit" | "offsetDirection">
): string {
  const unit =
    rule.offsetUnit === "hours"
      ? rule.offsetValue === 1
        ? "Hour"
        : "Hours"
      : rule.offsetUnit === "days"
        ? rule.offsetValue === 1
          ? "Day"
          : "Days"
        : rule.offsetUnit === "weeks"
          ? rule.offsetValue === 1
            ? "Week"
            : "Weeks"
          : rule.offsetValue === 1
            ? "Month"
            : "Months";
  const direction = rule.offsetDirection === "before" ? "Before" : "After";
  return `${rule.offsetValue} ${unit} ${direction}`;
}

/** Validate one draft rule before adding/updating the configured list. */
export function validateRelativeReminderRuleDraft(
  rule: Pick<RelativeReminderRule, "offsetValue" | "offsetUnit" | "offsetDirection">,
  existing: RelativeReminderRule[],
  options?: { excludeId?: string }
): string | null {
  if (!Number.isFinite(rule.offsetValue) || rule.offsetValue < 0) {
    return "Offset value must be zero or a positive number.";
  }
  if (!Number.isInteger(rule.offsetValue)) {
    return "Offset value must be a whole number.";
  }
  if (!rule.offsetUnit) {
    return "Offset unit is required.";
  }
  if (!rule.offsetDirection) {
    return "Direction is required.";
  }

  const key = relativeRuleKey(rule);
  const duplicate = existing.some(
    (item) => item.id !== options?.excludeId && relativeRuleKey(item) === key
  );
  if (duplicate) {
    return `Duplicate relative reminder rule: ${formatRelativeReminderRuleLabel(rule)}.`;
  }
  return null;
}

export function validateRelativeReminderRules(rules: RelativeReminderRule[]): string | null {
  if (!rules.length) {
    return "Add at least one relative reminder rule.";
  }

  const seen = new Set<string>();
  for (let index = 0; index < rules.length; index += 1) {
    const rule = rules[index];
    const row = index + 1;

    if (!Number.isFinite(rule.offsetValue) || rule.offsetValue < 0) {
      return `Rule ${row}: offset value must be zero or a positive number.`;
    }
    if (!Number.isInteger(rule.offsetValue)) {
      return `Rule ${row}: offset value must be a whole number.`;
    }
    if (!rule.offsetUnit) {
      return `Rule ${row}: offset unit is required.`;
    }
    if (!rule.offsetDirection) {
      return `Rule ${row}: direction is required.`;
    }

    const key = relativeRuleKey(rule);
    if (seen.has(key)) {
      return `Duplicate relative reminder rule: ${formatRelativeReminderRuleLabel(rule)}.`;
    }
    seen.add(key);
  }

  return null;
}

export function syncLegacyOffsetFieldsFromRules(rules: RelativeReminderRule[]): {
  offsetValue: number;
  offsetUnit: RelativeReminderOffsetUnit;
  offsetDirection: RelativeReminderOffsetDirection;
} {
  const first = rules[0];
  if (!first) {
    return {
      offsetValue: 24,
      offsetUnit: "hours",
      offsetDirection: "before",
    };
  }
  return {
    offsetValue: first.offsetValue,
    offsetUnit: first.offsetUnit,
    offsetDirection: first.offsetDirection,
  };
}
