import {
  REMINDER_HISTORY_STATUS_OPTIONS,
  REMINDER_STATUS_OPTIONS,
  comboboxClassName,
  fieldClassName,
} from "../../lib/reminder-management/constants";
import { useReminderChannels, useReminderModules } from "../../lib/reminder-management/hooks";
import { rememberModuleLabel } from "../../lib/reminder-management/format";
import type {
  ReminderHistoryFilters,
  ReminderListFilters,
} from "../../lib/reminder-management/types";
import Combobox from "../ui/Combobox";

type ListFiltersProps = {
  value: ReminderListFilters;
  onChange: (next: ReminderListFilters) => void;
};

function withPageReset(value: ReminderListFilters, patch: Partial<ReminderListFilters>): ReminderListFilters {
  return { ...value, ...patch, page: 0 };
}

export function ReminderListFiltersBar({ value, onChange }: ListFiltersProps) {
  const modulesQuery = useReminderModules();
  const channelsQuery = useReminderChannels();
  const modules = modulesQuery.data ?? [];
  const channels = channelsQuery.data ?? [];

  for (const module of modules) {
    rememberModuleLabel(module.value, module.label);
  }

  const moduleItems = [
    { value: "all", label: "All modules" },
    ...modules.map((option) => ({ value: option.value, label: option.label })),
  ];
  const statusItems = [
    { value: "all", label: "All statuses" },
    ...REMINDER_STATUS_OPTIONS.map((option) => ({ value: option.value, label: option.label })),
  ];
  const channelItems = [
    { value: "all", label: "All channels" },
    ...channels.map((option) => ({ value: option.key, label: option.label })),
  ];

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <label className="block">
        <span className="sr-only">Search</span>
        <input
          className={fieldClassName}
          placeholder="Search reminders…"
          value={value.search}
          onChange={(event) => onChange(withPageReset(value, { search: event.target.value }))}
        />
      </label>
      <Combobox
        items={moduleItems}
        value={value.module}
        onChange={(next) =>
          onChange(
            withPageReset(value, {
              module: (next || "all") as ReminderListFilters["module"],
            })
          )
        }
        placeholder="All modules"
        searchable={false}
        className={comboboxClassName}
      />
      <Combobox
        items={statusItems}
        value={value.status}
        onChange={(next) =>
          onChange(
            withPageReset(value, {
              status: (next || "all") as ReminderListFilters["status"],
            })
          )
        }
        placeholder="All statuses"
        searchable={false}
        className={comboboxClassName}
      />
      <Combobox
        items={channelItems}
        value={value.channel}
        onChange={(next) =>
          onChange(
            withPageReset(value, {
              channel: (next || "all") as ReminderListFilters["channel"],
            })
          )
        }
        placeholder="All channels"
        searchable={false}
        className={comboboxClassName}
      />
    </div>
  );
}

type HistoryFiltersProps = {
  value: ReminderHistoryFilters;
  onChange: (next: ReminderHistoryFilters) => void;
};

function withHistoryPageReset(
  value: ReminderHistoryFilters,
  patch: Partial<ReminderHistoryFilters>
): ReminderHistoryFilters {
  return { ...value, ...patch, page: 0 };
}

export function ReminderHistoryFiltersBar({ value, onChange }: HistoryFiltersProps) {
  const modulesQuery = useReminderModules();
  const channelsQuery = useReminderChannels();
  const modules = modulesQuery.data ?? [];
  const channels = channelsQuery.data ?? [];

  for (const module of modules) {
    rememberModuleLabel(module.value, module.label);
  }

  const moduleItems = [
    { value: "all", label: "All modules" },
    ...modules.map((option) => ({ value: option.value, label: option.label })),
  ];
  const statusItems = [
    { value: "all", label: "All statuses" },
    ...REMINDER_HISTORY_STATUS_OPTIONS.map((option) => ({
      value: option.value,
      label: option.label,
    })),
  ];
  const channelItems = [
    { value: "all", label: "All channels" },
    ...channels.map((option) => ({ value: option.key, label: option.label })),
  ];

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
      <label className="block">
        <span className="sr-only">Search</span>
        <input
          className={fieldClassName}
          placeholder="Search title or recipient…"
          value={value.search}
          onChange={(event) => onChange(withHistoryPageReset(value, { search: event.target.value }))}
        />
      </label>
      <Combobox
        items={moduleItems}
        value={value.module}
        onChange={(next) =>
          onChange(
            withHistoryPageReset(value, {
              module: (next || "all") as ReminderHistoryFilters["module"],
            })
          )
        }
        placeholder="All modules"
        searchable={false}
        className={comboboxClassName}
      />
      <Combobox
        items={statusItems}
        value={value.status}
        onChange={(next) =>
          onChange(
            withHistoryPageReset(value, {
              status: (next || "all") as ReminderHistoryFilters["status"],
            })
          )
        }
        placeholder="All statuses"
        searchable={false}
        className={comboboxClassName}
      />
      <Combobox
        items={channelItems}
        value={value.channel}
        onChange={(next) =>
          onChange(
            withHistoryPageReset(value, {
              channel: (next || "all") as ReminderHistoryFilters["channel"],
            })
          )
        }
        placeholder="All channels"
        searchable={false}
        className={comboboxClassName}
      />
      <input
        type="date"
        className={fieldClassName}
        value={value.dateFrom}
        onChange={(event) =>
          onChange(withHistoryPageReset(value, { dateFrom: event.target.value }))
        }
        aria-label="From date"
      />
      <input
        type="date"
        className={fieldClassName}
        value={value.dateTo}
        onChange={(event) => onChange(withHistoryPageReset(value, { dateTo: event.target.value }))}
        aria-label="To date"
      />
    </div>
  );
}
