import { describe, expect, it } from "vitest";

import {
  createRelativeReminderRule,
  createRelativeReminderRuleId,
  formatRelativeReminderRuleLabel,
  validateRelativeReminderRuleDraft,
  validateRelativeReminderRules,
} from "./relative-rules";
import {
  buildRelativeReminderConfigCreateInput,
  draftToReminderConfigDefinitions,
  RELATIVE_REMINDER_ORG_ENTITY_ID,
} from "./relative-config-api";
import { emptyPersonalReminderDraft } from "../personal-reminders/api";

describe("relative reminder multi-rule helpers", () => {
  it("createRelativeReminderRuleId uses randomUUID when available", () => {
    const original = globalThis.crypto;
    Object.defineProperty(globalThis, "crypto", {
      value: { randomUUID: () => "uuid-test-1234" },
      configurable: true,
    });
    try {
      expect(createRelativeReminderRuleId()).toBe("uuid-test-1234");
    } finally {
      Object.defineProperty(globalThis, "crypto", {
        value: original,
        configurable: true,
      });
    }
  });

  it("createRelativeReminderRuleId falls back when randomUUID is missing", () => {
    const original = globalThis.crypto;
    Object.defineProperty(globalThis, "crypto", {
      value: {},
      configurable: true,
    });
    try {
      const id = createRelativeReminderRuleId();
      expect(id).toMatch(/^rule-\d+-[a-z0-9]+$/);
    } finally {
      Object.defineProperty(globalThis, "crypto", {
        value: original,
        configurable: true,
      });
    }
  });

  it("formats compact rule labels", () => {
    expect(
      formatRelativeReminderRuleLabel({
        offsetValue: 24,
        offsetUnit: "hours",
        offsetDirection: "before",
      })
    ).toBe("24 Hours Before");
    expect(
      formatRelativeReminderRuleLabel({
        offsetValue: 1,
        offsetUnit: "days",
        offsetDirection: "after",
      })
    ).toBe("1 Day After");
  });

  it("rejects empty and duplicate rules", () => {
    expect(validateRelativeReminderRules([])).toMatch(/at least one/i);

    const duplicate = [
      createRelativeReminderRule({ offsetValue: 30, offsetUnit: "days", offsetDirection: "before" }),
      createRelativeReminderRule({ offsetValue: 30, offsetUnit: "days", offsetDirection: "before" }),
    ];
    expect(validateRelativeReminderRules(duplicate)).toMatch(/duplicate/i);
  });

  it("validates a draft rule without treating the edited row as a duplicate", () => {
    const existing = [
      createRelativeReminderRule({
        id: "rule-1",
        offsetValue: 7,
        offsetUnit: "days",
        offsetDirection: "before",
      }),
    ];
    expect(
      validateRelativeReminderRuleDraft(
        { offsetValue: 7, offsetUnit: "days", offsetDirection: "before" },
        existing
      )
    ).toMatch(/duplicate/i);
    expect(
      validateRelativeReminderRuleDraft(
        { offsetValue: 7, offsetUnit: "days", offsetDirection: "before" },
        existing,
        { excludeId: "rule-1" }
      )
    ).toBeNull();
  });

  it("maps each rule into a separate reminder definition sharing trigger and channels", () => {
    const draft = emptyPersonalReminderDraft({
      triggerType: "relative",
      title: "Policy Expiry Cadence",
      moduleKey: "policy",
      triggerKey: "expiry_date",
      triggerKind: "date",
      channels: ["whatsapp", "in_app"],
      relativeRules: [
        createRelativeReminderRule({ offsetValue: 30, offsetUnit: "days", offsetDirection: "before" }),
        createRelativeReminderRule({ offsetValue: 7, offsetUnit: "days", offsetDirection: "before" }),
        createRelativeReminderRule({ offsetValue: 24, offsetUnit: "hours", offsetDirection: "after" }),
      ],
    });

    const definitions = draftToReminderConfigDefinitions(draft);
    expect(definitions).toHaveLength(3);
    expect(definitions.map((item) => item.offset_value)).toEqual([30, 7, 24]);
    expect(definitions.every((item) => item.anchor_key === "expiry_date")).toBe(true);
    expect(definitions.every((item) => item.channels?.join(",") === "whatsapp,in_app")).toBe(true);

    const payload = buildRelativeReminderConfigCreateInput({
      organizationId: 607,
      draft,
      templateKey: "policy_renewal_reminder",
    });
    expect(payload.entity_id).toBe(RELATIVE_REMINDER_ORG_ENTITY_ID);
    expect(payload.reminders).toHaveLength(3);
    expect(payload.entity_label).toBe("Policy Expiry Cadence");
  });

  it("starts with no configured rules and falls back to legacy offset when relativeRules is empty", () => {
    const draft = emptyPersonalReminderDraft({
      triggerType: "relative",
      moduleKey: "policy",
      triggerKey: "expiry_date",
      offsetValue: 15,
      offsetUnit: "days",
      offsetDirection: "before",
    });
    expect(draft.relativeRules).toEqual([]);

    const forced = { ...draft, relativeRules: [] as typeof draft.relativeRules };
    const definitions = draftToReminderConfigDefinitions(forced);
    expect(definitions).toHaveLength(1);
    expect(definitions[0].offset_value).toBe(15);
    expect(definitions[0].offset_unit).toBe("days");
  });
});
