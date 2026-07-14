import React, { useMemo, useState } from "react";
import Combobox from "../ui/Combobox";
import {
  computeCustomRemindersPreview,
  formatCustomReminderBeforeExpiryLabel,
  getRenewalReminderValueBounds,
  PERSONALIZED_REMINDER_UNIT_OPTIONS,
  sanitizeReminderUnit,
  validateRenewalReminderValue,
  type CustomReminderItem,
  type ReminderUnit,
} from "../../lib/insurance/custom-reminder-config";

type PersonalizedReminderBuilderProps = {
  expiryDateIso: string | null;
  customReminders: CustomReminderItem[];
  onCustomRemindersChange: (reminders: CustomReminderItem[]) => void;
  dndStart: string;
  dndEnd: string;
  onDndStartChange: (value: string) => void;
  onDndEndChange: (value: string) => void;
  dndError?: string | null;
  onDndErrorClear?: () => void;
  remindersError?: string | null;
  labelClassName: string;
  fieldClassName: string;
  comboboxClassName: string;
};

const listActionClassName =
  "inline-flex items-center rounded-lg border border-slate-300/80 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-2.5 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 transition hover:border-[#14B8A6]/40 hover:bg-[#14B8A6]/10 hover:text-slate-900 dark:hover:text-white";

export function PersonalizedReminderBuilder({
  expiryDateIso,
  customReminders,
  onCustomRemindersChange,
  dndStart,
  dndEnd,
  onDndStartChange,
  onDndEndChange,
  dndError,
  onDndErrorClear,
  remindersError,
  labelClassName,
  fieldClassName,
  comboboxClassName,
}: PersonalizedReminderBuilderProps) {
  const [builderUnit, setBuilderUnit] = useState<ReminderUnit>("days");
  const [builderValue, setBuilderValue] = useState("7");
  const [builderValueError, setBuilderValueError] = useState<string | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const valueBounds = getRenewalReminderValueBounds(builderUnit);

  const previewLines = useMemo(
    () => computeCustomRemindersPreview(expiryDateIso, customReminders),
    [customReminders, expiryDateIso]
  );

  function resetBuilder() {
    setBuilderUnit("days");
    setBuilderValue("7");
    setBuilderValueError(null);
    setEditingIndex(null);
  }

  function handleUnitChange(rawUnit: string) {
    const nextUnit = sanitizeReminderUnit(rawUnit);
    setBuilderUnit(nextUnit);
    setBuilderValueError(null);
    const bounds = getRenewalReminderValueBounds(nextUnit);
    setBuilderValue(String(nextUnit === "days" ? 7 : bounds.max));
  }

  function handleAddOrUpdateReminder() {
    const valueError = validateRenewalReminderValue(builderUnit, builderValue);
    if (valueError) {
      setBuilderValueError(valueError);
      return;
    }

    const parsedValue = Number(builderValue);
    const nextItem: CustomReminderItem = {
      reminder_unit: builderUnit,
      reminder_value: parsedValue,
    };

    if (editingIndex !== null) {
      const updated = customReminders.map((item, index) => (index === editingIndex ? nextItem : item));
      onCustomRemindersChange(updated);
    } else {
      onCustomRemindersChange([...customReminders, nextItem]);
    }

    resetBuilder();
  }

  function handleEditReminder(index: number) {
    const item = customReminders[index];
    if (!item) {
      return;
    }
    setEditingIndex(index);
    setBuilderUnit(item.reminder_unit);
    setBuilderValue(String(item.reminder_value));
    setBuilderValueError(null);
  }

  function handleRemoveReminder(index: number) {
    onCustomRemindersChange(customReminders.filter((_, itemIndex) => itemIndex !== index));
    if (editingIndex === index) {
      resetBuilder();
    } else if (editingIndex !== null && index < editingIndex) {
      setEditingIndex(editingIndex - 1);
    }
  }

  return (
    <div className="space-y-4 rounded-xl border border-slate-300/60 bg-white/70 dark:border-white/[0.06] dark:bg-slate-950/25 p-4 pt-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="block">
          <span className={labelClassName}>Reminder Unit</span>
          <Combobox
            items={PERSONALIZED_REMINDER_UNIT_OPTIONS}
            value={builderUnit}
            onChange={(value) => {
              if (!value) return;
              handleUnitChange(value);
            }}
            placeholder="Select unit"
            searchable={false}
            className={comboboxClassName}
          />
        </label>
        <label className="block">
          <span className={labelClassName}>
            Reminder Value ({valueBounds.min}–{valueBounds.max})
          </span>
          <input
            type="number"
            min={valueBounds.min}
            max={valueBounds.max}
            step={1}
            value={builderValue}
            onChange={(event) => {
              setBuilderValueError(null);
              setBuilderValue(event.target.value);
            }}
            onBlur={() => setBuilderValueError(validateRenewalReminderValue(builderUnit, builderValue))}
            className={`${fieldClassName}${builderValueError ? " border-red-500/70 focus-visible:ring-red-500/30" : ""}`}
            placeholder="Enter value"
          />
          {builderValueError ? <p className="mt-2 text-sm text-red-400">{builderValueError}</p> : null}
        </label>
      </div>

      <div>
        <p className={`${labelClassName} mb-3`}>Do Not Disturb Hours</p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block">
            <span className={labelClassName}>Start Time</span>
            <input
              type="time"
              value={dndStart}
              onChange={(event) => {
                onDndErrorClear?.();
                onDndStartChange(event.target.value);
              }}
              className={fieldClassName}
            />
          </label>
          <label className="block">
            <span className={labelClassName}>End Time</span>
            <input
              type="time"
              value={dndEnd}
              onChange={(event) => {
                onDndErrorClear?.();
                onDndEndChange(event.target.value);
              }}
              className={fieldClassName}
            />
          </label>
        </div>
        {dndError ? <p className="mt-2 text-sm text-red-400">{dndError}</p> : null}
      </div>

      <div>
        <button
          type="button"
          onClick={handleAddOrUpdateReminder}
          className="inline-flex items-center rounded-xl border border-[#14B8A6]/30 bg-[#14B8A6]/10 px-4 py-2.5 text-sm font-medium text-[#14B8A6] transition hover:border-[#14B8A6]/50 hover:bg-[#14B8A6]/15"
        >
          {editingIndex !== null ? "Update Reminder" : "+ Add Reminder"}
        </button>
        {editingIndex !== null ? (
          <button
            type="button"
            onClick={resetBuilder}
            className="ml-3 inline-flex items-center rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 dark:text-slate-400 transition hover:text-slate-900 dark:hover:text-white"
          >
            Cancel Edit
          </button>
        ) : null}
      </div>

      <div>
        <p className={`${labelClassName} mb-3`}>Configured Reminders</p>
        {customReminders.length === 0 ? (
          <p className="text-sm text-slate-600 dark:text-slate-500">No reminders configured yet. Use the builder above to add one.</p>
        ) : (
          <ul className="space-y-2">
            {customReminders.map((item, index) => (
              <li
                key={`${item.reminder_unit}-${item.reminder_value}-${index}`}
                className="flex flex-col gap-3 rounded-xl border border-slate-300/60 bg-white/85 dark:border-white/[0.06] dark:bg-slate-950/40 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="text-sm text-slate-700 dark:text-slate-200">
                  • {formatCustomReminderBeforeExpiryLabel(item.reminder_unit, item.reminder_value)}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleEditReminder(index)}
                    className={listActionClassName}
                  >
                    ✏ Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRemoveReminder(index)}
                    className={listActionClassName}
                  >
                    🗑 Remove
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
        {remindersError ? <p className="mt-2 text-sm text-red-400">{remindersError}</p> : null}
      </div>

      <div className="rounded-xl border border-[#14B8A6]/25 bg-[#14B8A6]/10 px-4 py-3 text-sm text-slate-700 dark:text-slate-200">
        <p className="font-semibold text-[#14B8A6]">Reminder Preview</p>
        {previewLines.length > 0 ? (
          <ul className="mt-2 space-y-1">
            {previewLines.map((line) => (
              <li key={`${line.label}-${line.previewDate}`}>
                <span className="text-slate-600 dark:text-slate-400">• {line.label}</span>
                <span className="text-slate-500 dark:text-slate-500"> → </span>
                <span className="font-medium text-slate-900 dark:text-white">{line.previewDate}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            Enter a valid expiry date and add reminders to preview the schedule.
          </p>
        )}
      </div>
    </div>
  );
}

export default PersonalizedReminderBuilder;
