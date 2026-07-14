import { describe, expect, it } from "vitest";
import {
  buildPolicyReminderSettingsPayload,
  computeCustomRemindersPreview,
  computePersonalizedReminderPreview,
  computeReminderPreview,
  formatCustomReminderBeforeExpiryLabel,
  getReminderValueBounds,
  getRenewalReminderValueBounds,
  maxMonthsForRenewalFrequency,
  RENEWAL_REMINDER_UNIT_SELECT_OPTIONS,
  sanitizeReminderUnit,
  validateRenewalReminderValue,
  validateReminderValue,
  PERSONALIZED_REMINDER_UNIT_OPTIONS,
} from "./custom-reminder-config";

describe("custom-reminder-config", () => {
  it("returns unit-specific reminder value bounds", () => {
    expect(getReminderValueBounds("hours")).toEqual({ min: 1, max: 24 });
    expect(getReminderValueBounds("days")).toEqual({ min: 1, max: 7 });
    expect(getReminderValueBounds("weeks")).toEqual({ min: 1, max: 4 });
    expect(getReminderValueBounds("months", "quarterly")).toEqual({ min: 1, max: 3 });
  });

  it("returns fixed renewal reminder bounds including hours and months up to 12", () => {
    expect(getRenewalReminderValueBounds("hours")).toEqual({ min: 1, max: 24 });
    expect(getRenewalReminderValueBounds("months")).toEqual({ min: 1, max: 12 });
  });

  it("keeps renewal reminder unit options static and excludes time values", () => {
    expect(RENEWAL_REMINDER_UNIT_SELECT_OPTIONS.map((option) => option.label)).toEqual([
      "Hours",
      "Days",
      "Weeks",
      "Months",
    ]);
    expect(PERSONALIZED_REMINDER_UNIT_OPTIONS.map((option) => option.label)).toEqual([
      "Hours",
      "Days",
      "Weeks",
      "Months",
    ]);
    expect(sanitizeReminderUnit("21:00")).toBe("days");
    expect(sanitizeReminderUnit("hours")).toBe("hours");
  });

  it("formats hour-based personalized schedules", () => {
    const expiry = new Date(2026, 5, 24, 12, 0, 0);
    const preview = computePersonalizedReminderPreview(expiry.toISOString(), "hours", 6);
    expect(preview?.schedule).toBe("Reminder will be sent 6 hours before expiry");
  });

  it("validates renewal reminder values with fixed month bounds", () => {
    expect(validateRenewalReminderValue("months", "13")).toMatch(/between 1 and 12/);
    expect(validateRenewalReminderValue("hours", "12")).toBeNull();
  });

  it("limits months by renewal frequency", () => {
    expect(maxMonthsForRenewalFrequency("monthly")).toBe(1);
    expect(maxMonthsForRenewalFrequency("yearly")).toBe(12);
  });

  it("validates reminder values", () => {
    expect(validateReminderValue("hours", "25", "yearly")).toMatch(/between 1 and 24/);
    expect(validateReminderValue("months", "4", "quarterly")).toMatch(/between 1 and 3/);
    expect(validateReminderValue("days", "3", "yearly")).toBeNull();
  });

  it("computes reminder preview before expiry", () => {
    const expiry = new Date(2026, 6, 18, 12, 0, 0);
    const preview = computeReminderPreview(expiry.toISOString(), "days", 5);
    expect(preview?.reminderDate).toBe("13-07-2026");
    expect(preview?.reminderDay).toBeTruthy();
    expect(preview?.reminderTime).toBeNull();
  });

  it("includes time for hour-based reminders", () => {
    const expiry = new Date(2026, 6, 18, 12, 0, 0);
    const preview = computeReminderPreview(expiry.toISOString(), "hours", 2);
    expect(preview?.reminderTime).toBeTruthy();
  });

  it("formats personalized reminder preview from expiry date", () => {
    const expiry = new Date(2027, 0, 12, 12, 0, 0);

    const daysPreview = computePersonalizedReminderPreview(expiry.toISOString(), "days", 7);
    expect(daysPreview?.schedule).toBe("Reminder will be sent 7 days before expiry");
    expect(daysPreview?.nextReminder).toBe("05-01-2027");

    const weeksPreview = computePersonalizedReminderPreview(expiry.toISOString(), "weeks", 2);
    expect(weeksPreview?.schedule).toBe("Reminder will be sent 2 weeks before expiry");
    expect(weeksPreview?.nextReminder).toBe("29-12-2026");

    const monthsPreview = computePersonalizedReminderPreview(expiry.toISOString(), "months", 1);
    expect(monthsPreview?.schedule).toBe("Reminder will be sent 1 month before expiry");
    expect(monthsPreview?.nextReminder).toBe("13-12-2026");
  });

  it("formats multi-reminder labels and preview lines", () => {
    const expiry = new Date(2027, 0, 12, 12, 0, 0).toISOString();
    const reminders = [
      { reminder_unit: "hours" as const, reminder_value: 12 },
      { reminder_unit: "days" as const, reminder_value: 7 },
      { reminder_unit: "weeks" as const, reminder_value: 2 },
      { reminder_unit: "months" as const, reminder_value: 1 },
    ];

    expect(formatCustomReminderBeforeExpiryLabel("days", 1)).toBe("1 day before expiry");
    expect(formatCustomReminderBeforeExpiryLabel("days", 2)).toBe("2 days before expiry");
    expect(formatCustomReminderBeforeExpiryLabel("weeks", 1)).toBe("1 week before expiry");
    expect(formatCustomReminderBeforeExpiryLabel("weeks", 2)).toBe("2 weeks before expiry");

    const preview = computeCustomRemindersPreview(expiry, reminders);
    expect(preview).toHaveLength(4);
    expect(preview[0]?.label).toBe("12 hours before expiry");
    expect(preview[0]?.previewDate).toMatch(/12:00/i);
  });

  it("builds default and personalized reminder payloads", () => {
    expect(
      buildPolicyReminderSettingsPayload({
        reminderType: "default",
        preferredChannels: ["whatsapp"],
      })
    ).toEqual({
      reminder_type: "default",
      preferred_channel: ["whatsapp"],
      default_cycle_days: [30, 15, 10, 5, 2, 1, 0],
    });

    expect(
      buildPolicyReminderSettingsPayload({
        reminderType: "personalized",
        preferredChannels: ["email"],
        personalizedUnit: "weeks",
        personalizedValue: "2",
        doNotDisturbStart: "21:00",
        doNotDisturbEnd: "08:00",
      }).personalized
    ).toEqual({
      unit: "weeks",
      value: 2,
      do_not_disturb_start: "21:00",
      do_not_disturb_end: "08:00",
    });
  });
});
