import { useState } from "react";

import Combobox from "../ui/Combobox";
import {
  comboboxClassName,
  fieldClassName,
  labelClassName,
  REMINDER_DIRECTION_OPTIONS,
  REMINDER_OFFSET_UNIT_OPTIONS,
} from "../../lib/reminder-management/constants";
import {
  createRelativeReminderRule,
  formatRelativeReminderRuleLabel,
  syncLegacyOffsetFieldsFromRules,
  validateRelativeReminderRuleDraft,
} from "../../lib/reminder-management/relative-rules";
import type {
  RelativeReminderOffsetDirection,
  RelativeReminderOffsetUnit,
  RelativeReminderRule,
} from "../../lib/personal-reminders/types";
import { NormalizedNumberInput } from "./NormalizedNumberInput";

type RelativeReminderRulesFieldsProps = {
  rules: RelativeReminderRule[];
  onChange: (rules: RelativeReminderRule[]) => void;
  offsetUnitOptions?: ReadonlyArray<{ value: RelativeReminderOffsetUnit; label: string }>;
};

type EditorState = {
  /** null = creating; string = editing that rule id */
  editingId: string | null;
  offsetValue: number;
  offsetUnit: RelativeReminderOffsetUnit;
  offsetDirection: RelativeReminderOffsetDirection;
};

const compactFieldClassName = `${fieldClassName} h-10 px-3`;
const compactComboboxClassName = `${comboboxClassName} h-10`;

function emptyEditorState(): EditorState {
  return {
    editingId: null,
    offsetValue: 24,
    offsetUnit: "hours",
    offsetDirection: "before",
  };
}

export function RelativeReminderRulesFields({
  rules,
  onChange,
  offsetUnitOptions = REMINDER_OFFSET_UNIT_OPTIONS.filter((option) => option.value !== "minutes"),
}: RelativeReminderRulesFieldsProps) {
  const [editorOpen, setEditorOpen] = useState(false);
  const [editor, setEditor] = useState<EditorState>(emptyEditorState);
  const [editorError, setEditorError] = useState<string | null>(null);

  const configured = rules;

  const closeEditor = () => {
    setEditorOpen(false);
    setEditor(emptyEditorState());
    setEditorError(null);
  };

  const openCreateEditor = () => {
    setEditor(emptyEditorState());
    setEditorError(null);
    setEditorOpen(true);
  };

  const openEditEditor = (rule: RelativeReminderRule) => {
    setEditor({
      editingId: rule.id,
      offsetValue: rule.offsetValue,
      offsetUnit: rule.offsetUnit,
      offsetDirection: rule.offsetDirection,
    });
    setEditorError(null);
    setEditorOpen(true);
  };

  const commitEditor = () => {
    const draft = {
      offsetValue: editor.offsetValue,
      offsetUnit: editor.offsetUnit,
      offsetDirection: editor.offsetDirection,
    };
    const error = validateRelativeReminderRuleDraft(draft, configured, {
      excludeId: editor.editingId ?? undefined,
    });
    if (error) {
      setEditorError(error);
      return;
    }

    if (editor.editingId) {
      onChange(
        configured.map((rule) =>
          rule.id === editor.editingId ? { ...rule, ...draft } : rule
        )
      );
    } else {
      onChange([...configured, createRelativeReminderRule(draft)]);
    }
    closeEditor();
  };

  const removeRule = (id: string) => {
    onChange(configured.filter((rule) => rule.id !== id));
    if (editor.editingId === id) {
      closeEditor();
    }
  };

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
          Configured Relative Reminder Rules
        </h4>
        {configured.length > 0 ? (
          <span className="text-[11px] text-slate-500 dark:text-slate-500">
            {configured.length} rule{configured.length === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>

      {configured.length > 0 ? (
        <ul className="overflow-hidden rounded-xl border border-slate-300/70 dark:border-white/[0.08] divide-y divide-slate-300/60 dark:divide-white/[0.08]">
          {configured.map((rule) => (
            <li
              key={rule.id}
              className="flex items-center gap-3 px-3 py-2.5 bg-white/60 dark:bg-slate-950/30"
            >
              <span
                className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#14B8A6]/15 text-[#14B8A6]"
                aria-hidden
              >
                ✓
              </span>
              <span className="min-w-0 flex-1 text-sm font-medium text-slate-800 dark:text-slate-100">
                {formatRelativeReminderRuleLabel(rule)}
              </span>
              <div className="flex shrink-0 items-center gap-1">
                <button
                  type="button"
                  className="rounded-lg px-2 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/5 dark:hover:text-white"
                  onClick={() => openEditEditor(rule)}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 transition hover:bg-rose-500/10 hover:text-rose-400"
                  aria-label={`Delete ${formatRelativeReminderRuleLabel(rule)}`}
                  title="Delete rule"
                  onClick={() => removeRule(rule.id)}
                >
                  <TrashIcon />
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : !editorOpen ? (
        <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-500">
          No relative reminder rules yet. Add offsets for this trigger (for example 30 days before,
          7 days before, 24 hours after).
        </p>
      ) : null}

      {editorOpen ? (
        <div className="space-y-3 rounded-xl border border-slate-300/70 bg-slate-50/80 p-3 dark:border-white/[0.08] dark:bg-white/[0.03]">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-500">
            {editor.editingId ? "Edit Relative Reminder" : "New Relative Reminder"}
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block min-w-0">
              <span className={labelClassName}>Offset Value</span>
              <NormalizedNumberInput
                min={0}
                step={1}
                className={compactFieldClassName}
                value={editor.offsetValue}
                onChange={(offsetValue) => {
                  setEditorError(null);
                  setEditor((current) => ({ ...current, offsetValue }));
                }}
              />
            </label>
            <label className="block min-w-0">
              <span className={labelClassName}>Offset Unit</span>
              <Combobox
                items={offsetUnitOptions.map((option) => ({
                  value: option.value,
                  label: option.label,
                }))}
                value={editor.offsetUnit}
                onChange={(next) => {
                  setEditorError(null);
                  setEditor((current) => ({
                    ...current,
                    offsetUnit: (next || "days") as RelativeReminderOffsetUnit,
                  }));
                }}
                placeholder="Unit"
                searchable={false}
                className={compactComboboxClassName}
              />
            </label>
            <label className="block min-w-0">
              <span className={labelClassName}>Direction</span>
              <Combobox
                items={REMINDER_DIRECTION_OPTIONS.map((option) => ({
                  value: option.value,
                  label: option.label,
                }))}
                value={editor.offsetDirection}
                onChange={(next) => {
                  setEditorError(null);
                  setEditor((current) => ({
                    ...current,
                    offsetDirection: (next || "before") as RelativeReminderOffsetDirection,
                  }));
                }}
                placeholder="Direction"
                searchable={false}
                className={compactComboboxClassName}
              />
            </label>
          </div>
          {editorError ? <p className="text-sm text-rose-400">{editorError}</p> : null}
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              onClick={closeEditor}
              className="inline-flex items-center rounded-xl px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-white/5"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={commitEditor}
              className="inline-flex items-center rounded-xl bg-[#14B8A6] px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-[#2dd4bf]"
            >
              {editor.editingId ? "Save Rule" : "Add Rule"}
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={openCreateEditor}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-[#14B8A6] transition hover:bg-[#14B8A6]/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40"
        >
          <span aria-hidden className="text-base leading-none">
            +
          </span>
          Add Relative Reminder
        </button>
      )}
    </section>
  );
}

/** Apply rule-list changes onto a draft patch including legacy single-offset mirrors. */
export function relativeRulesDraftPatch(rules: RelativeReminderRule[]) {
  return {
    relativeRules: rules,
    ...syncLegacyOffsetFieldsFromRules(rules),
  };
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4" aria-hidden>
      <path
        d="M7.5 4.5h5M4.5 6h11M8 9v4.5M12 9v4.5M6.5 6l.6 8.2a1.5 1.5 0 0 0 1.5 1.3h3.8a1.5 1.5 0 0 0 1.5-1.3L14.5 6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
