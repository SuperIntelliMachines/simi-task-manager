import React from "react";

interface Option {
  value: string;
  label: string;
}

interface MultiSelectProps {
  items: ReadonlyArray<string | Option>;
  value: string[];
  onChange: (value: string[]) => void;
  className?: string;
  columns?: 1 | 2;
}

export default function MultiSelect({
  items,
  value,
  onChange,
  className = "",
  columns = 2,
}: MultiSelectProps) {
  const normalized: Option[] = items.map((item) =>
    typeof item === "string" ? { value: item, label: item } : item
  );

  function toggle(optionValue: string) {
    if (value.includes(optionValue)) {
      onChange(value.filter((entry) => entry !== optionValue));
      return;
    }
    onChange([...value, optionValue]);
  }

  return (
    <div
      className={`multi-select multi-select-cols-${columns} ${className}`.trim()}
      role="group"
      aria-label="Reminder channels"
    >
      {normalized.map((option) => {
        const selected = value.includes(option.value);
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={selected}
            onClick={() => toggle(option.value)}
            className={`multi-select-chip${selected ? " multi-select-chip-selected" : ""}`}
          >
            <span className="multi-select-chip-check" aria-hidden="true">
              {selected ? "✓" : ""}
            </span>
            <span className="multi-select-chip-label">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
