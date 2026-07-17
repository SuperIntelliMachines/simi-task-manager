import Combobox from "../ui/Combobox";
import {
  comboboxClassName,
  fieldClassName,
  labelClassName,
  REMINDER_DIRECTION_OPTIONS,
  REMINDER_OFFSET_UNIT_OPTIONS,
  REMINDER_RECURRENCE_UNIT_OPTIONS,
  REMINDER_STOP_CONDITION_OPTIONS,
} from "../../lib/reminder-management/constants";
import type {
  ReminderOffsetDirection,
  ReminderOffsetUnit,
  ReminderRecurrenceUnit,
  ReminderStopCondition,
} from "../../lib/reminder-management/types";
import { NormalizedNumberInput } from "./NormalizedNumberInput";

export type ReminderSchedulingValues = {
  offsetValue: number;
  offsetUnit: ReminderOffsetUnit;
  offsetDirection: ReminderOffsetDirection;
  repeatEnabled: boolean;
  repeatFrequencyValue: number;
  repeatFrequencyUnit: ReminderRecurrenceUnit;
  maxAttempts: number | null;
  stopCondition: ReminderStopCondition;
};

type ReminderSchedulingFieldsProps = {
  value: ReminderSchedulingValues;
  onChange: (patch: Partial<ReminderSchedulingValues>) => void;
  offsetUnitOptions?: ReadonlyArray<{ value: ReminderOffsetUnit; label: string }>;
  stopConditionOptions?: ReadonlyArray<{ value: string; label: string }>;
  showTriggerOffset?: boolean;
  /** When "with-recurring", max attempts / stop condition appear only if recurring is enabled. */
  limitsMode?: "always" | "with-recurring";
  enableRecurringLabel?: string;
};

export function ReminderSchedulingFields({
  value,
  onChange,
  offsetUnitOptions = REMINDER_OFFSET_UNIT_OPTIONS.filter((option) => option.value !== "minutes"),
  stopConditionOptions = REMINDER_STOP_CONDITION_OPTIONS,
  showTriggerOffset = true,
  limitsMode = "always",
  enableRecurringLabel = "Enable Recurring",
}: ReminderSchedulingFieldsProps) {
  const showLimits =
    limitsMode === "always" || (limitsMode === "with-recurring" && value.repeatEnabled);

  return (
    <div className="space-y-4">
      {showTriggerOffset ? (
        <section className="space-y-2.5">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Trigger Offset</h4>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block min-w-0">
              <span className={labelClassName}>Offset Value</span>
              <NormalizedNumberInput
                min={0}
                step={1}
                className={fieldClassName}
                value={value.offsetValue}
                onChange={(offsetValue) => onChange({ offsetValue })}
              />
            </label>
            <label className="block min-w-0">
              <span className={labelClassName}>Offset Unit</span>
              <Combobox
                items={offsetUnitOptions.map((option) => ({
                  value: option.value,
                  label: option.label,
                }))}
                value={value.offsetUnit}
                onChange={(next) =>
                  onChange({ offsetUnit: (next || "days") as ReminderOffsetUnit })
                }
                placeholder="Select unit"
                searchable={false}
                className={comboboxClassName}
              />
            </label>
            <label className="block min-w-0">
              <span className={labelClassName}>Direction</span>
              <Combobox
                items={REMINDER_DIRECTION_OPTIONS.map((option) => ({
                  value: option.value,
                  label: option.label,
                }))}
                value={value.offsetDirection}
                onChange={(next) =>
                  onChange({
                    offsetDirection: (next || "after") as ReminderOffsetDirection,
                  })
                }
                placeholder="Select direction"
                searchable={false}
                className={comboboxClassName}
              />
            </label>
          </div>
        </section>
      ) : null}

      <section
        className={
          showTriggerOffset
            ? "space-y-2.5 border-t border-slate-300/50 dark:border-white/[0.08] pt-4"
            : "space-y-2.5"
        }
      >
        <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Recurring Reminder</h4>
        <label className="inline-flex cursor-pointer items-center gap-3 text-sm font-medium text-gray-800 dark:text-slate-200">
          <input
            type="checkbox"
            className="h-4 w-4 rounded accent-[#14B8A6]"
            checked={value.repeatEnabled}
            onChange={(event) => onChange({ repeatEnabled: event.target.checked })}
          />
          {enableRecurringLabel}
        </label>
        {value.repeatEnabled ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block min-w-0">
              <span className={labelClassName}>Repeat Every</span>
              <NormalizedNumberInput
                min={1}
                step={1}
                className={fieldClassName}
                value={value.repeatFrequencyValue}
                onChange={(repeatFrequencyValue) => onChange({ repeatFrequencyValue })}
              />
            </label>
            <label className="block min-w-0">
              <span className={labelClassName}>Unit</span>
              <Combobox
                items={REMINDER_RECURRENCE_UNIT_OPTIONS.map((option) => ({
                  value: option.value,
                  label: option.label,
                }))}
                value={value.repeatFrequencyUnit}
                onChange={(next) =>
                  onChange({
                    repeatFrequencyUnit: (next || "hours") as ReminderRecurrenceUnit,
                  })
                }
                placeholder="Select unit"
                searchable={false}
                className={comboboxClassName}
              />
            </label>
          </div>
        ) : null}
      </section>

      {showLimits ? (
        <section className="space-y-2.5 border-t border-slate-300/50 dark:border-white/[0.08] pt-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block min-w-0">
              <span className={labelClassName}>Maximum Attempts</span>
              <NormalizedNumberInput
                min={1}
                step={1}
                className={fieldClassName}
                value={value.maxAttempts}
                allowEmpty
                placeholder="Optional"
                onChange={(maxAttempts) => onChange({ maxAttempts })}
              />
              <p className="mt-1 text-[11px] leading-snug text-slate-500 dark:text-slate-500">
                Leave empty to continue until the stop condition is met.
              </p>
            </label>
            <label className="block min-w-0">
              <span className={labelClassName}>Stop Condition</span>
              <Combobox
                items={stopConditionOptions.map((option) => ({
                  value: option.value,
                  label: option.label,
                }))}
                value={value.stopCondition}
                onChange={(next) =>
                  onChange({
                    stopCondition: (next || "entity_ineligible") as ReminderStopCondition,
                  })
                }
                placeholder="Select stop condition"
                searchable={false}
                className={comboboxClassName}
              />
            </label>
          </div>
        </section>
      ) : null}
    </div>
  );
}
