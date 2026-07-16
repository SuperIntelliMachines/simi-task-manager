import { type ComponentProps, useEffect, useMemo, useRef, useState } from "react";
import { DayPicker, getDefaultClassNames } from "react-day-picker";
import "react-day-picker/style.css";
import { Calendar } from "../insurance/icons";
import {
  DATE_PICKER_MAX_ISO,
  DATE_PICKER_MIN_ISO,
  DISPLAY_DATE_MAX_LENGTH,
  formatDisplayDateInput,
  isoDateFromDisplay,
} from "../../lib/utils/date-display";
import { formatDate } from "../../lib/utils/formatDate";

const fieldClassName =
  "w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 h-12 placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-ring dark:bg-slate-900/50 dark:text-white dark:placeholder:text-slate-500 dark:border-slate-700";

const MIN_DATE = new Date(`${DATE_PICKER_MIN_ISO}T12:00:00.000Z`);
const MAX_DATE = new Date(`${DATE_PICKER_MAX_ISO}T12:00:00.000Z`);
const MIN_SELECTABLE_YEAR = new Date().getFullYear();
const MAX_SELECTABLE_YEAR = MAX_DATE.getUTCFullYear();

const MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] as const;

const SELECTABLE_YEARS = Array.from(
  { length: MAX_SELECTABLE_YEAR - MIN_SELECTABLE_YEAR + 1 },
  (_, index) => MIN_SELECTABLE_YEAR + index,
);

function displayToDate(display: string): Date | undefined {
  const iso = isoDateFromDisplay(display);
  if (!iso) return undefined;
  return new Date(`${iso}T12:00:00.000Z`);
}

function toVisibleMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1, 12, 0, 0, 0);
}

function clampVisibleMonth(date: Date): Date {
  const monthStart = toVisibleMonth(date);
  const minMonth = toVisibleMonth(MIN_DATE);
  const maxMonth = toVisibleMonth(MAX_DATE);

  if (monthStart < minMonth) {
    return minMonth;
  }
  if (monthStart > maxMonth) {
    return maxMonth;
  }
  return monthStart;
}

type InsuranceMonthYearPickerProps = {
  visibleMonth: Date;
  onSelect: (month: Date) => void;
  onBack: () => void;
};

function InsuranceMonthYearPicker({ visibleMonth, onSelect, onBack }: InsuranceMonthYearPickerProps) {
  const [pickerYear, setPickerYear] = useState(visibleMonth.getFullYear());
  const yearListRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setPickerYear(visibleMonth.getFullYear());
  }, [visibleMonth]);

  useEffect(() => {
    const activeYearButton = yearListRef.current?.querySelector<HTMLButtonElement>(
      `[data-year="${pickerYear}"]`,
    );
    activeYearButton?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [pickerYear]);

  function handleMonthSelect(monthIndex: number) {
    onSelect(clampVisibleMonth(new Date(pickerYear, monthIndex, 1, 12, 0, 0, 0)));
  }

  return (
    <div className="insurance-day-picker-view insurance-month-year-picker">
      <div className="insurance-month-year-picker-header">
        <button
          type="button"
          className="insurance-month-year-picker-back"
          onClick={onBack}
          aria-label="Back to calendar"
        >
          ←
        </button>
        <span className="insurance-month-year-picker-title">Select month &amp; year</span>
      </div>

      <div ref={yearListRef} className="insurance-month-year-picker-years" role="listbox" aria-label="Year">
        {SELECTABLE_YEARS.map((year) => {
          const isSelected = year === pickerYear;
          return (
            <button
              key={year}
              type="button"
              data-year={year}
              role="option"
              aria-selected={isSelected}
              className={`insurance-month-year-picker-year-btn${isSelected ? " is-selected" : ""}`}
              onClick={() => setPickerYear(year)}
            >
              {year}
            </button>
          );
        })}
      </div>

      <div className="insurance-month-year-picker-months" role="listbox" aria-label="Month">
        {MONTH_LABELS.map((label, monthIndex) => {
          const isCurrentMonth =
            pickerYear === visibleMonth.getFullYear() && monthIndex === visibleMonth.getMonth();
          return (
            <button
              key={label}
              type="button"
              role="option"
              aria-selected={isCurrentMonth}
              className={`insurance-month-year-picker-month-btn${isCurrentMonth ? " is-current" : ""}`}
              onClick={() => handleMonthSelect(monthIndex)}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

type InsuranceDatePickerProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string | null;
  onBlur?: () => void;
  inputClassName?: string;
  labelClassName?: string;
};

export function InsuranceDatePicker({
  label,
  value,
  onChange,
  placeholder = "DD-MM-YYYY",
  error = null,
  onBlur,
  inputClassName,
  labelClassName = "text-sm text-slate-700 dark:text-slate-300 mb-2",
}: InsuranceDatePickerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [placement, setPlacement] = useState<"below" | "above">("below");
  const [visibleMonth, setVisibleMonth] = useState<Date>(() => clampVisibleMonth(new Date()));
  const [monthYearPickerOpen, setMonthYearPickerOpen] = useState(false);
  const errorId = `${label.replace(/\s+/g, "-").toLowerCase()}-error`;
  const selectedDate = useMemo(() => displayToDate(value), [value]);
  const defaultClassNames = getDefaultClassNames();

  const dayPickerComponents = useMemo(
    () => ({
      CaptionLabel: ({ children, className, ...props }: ComponentProps<"span">) => (
        <button
          type="button"
          className={`insurance-day-picker-caption-btn ${className ?? ""}`}
          onClick={(event) => {
            event.preventDefault();
            setMonthYearPickerOpen(true);
          }}
          aria-expanded={monthYearPickerOpen}
          aria-label="Choose month and year"
        >
          {children}
        </button>
      ),
    }),
    [monthYearPickerOpen],
  );

  useEffect(() => {
    if (!open) return;
    const initialMonth = selectedDate ?? new Date();
    setVisibleMonth(clampVisibleMonth(initialMonth));
    setMonthYearPickerOpen(false);
  }, [open, selectedDate]);

  useEffect(() => {
    if (!open) return;

    function updatePlacement() {
      const trigger = containerRef.current;
      const popup = popupRef.current;
      if (!trigger) return;

      const rect = trigger.getBoundingClientRect();
      const popupHeight = popup?.offsetHeight ?? 320;
      const gap = 8;
      const spaceBelow = window.innerHeight - rect.bottom - gap;
      const spaceAbove = rect.top - gap;

      if (spaceBelow < popupHeight && spaceAbove > spaceBelow) {
        setPlacement("above");
      } else {
        setPlacement("below");
      }
    }

    // Measure after paint so popup height is accurate.
    const frame = window.requestAnimationFrame(updatePlacement);
    window.addEventListener("scroll", updatePlacement, true);
    window.addEventListener("resize", updatePlacement);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("scroll", updatePlacement, true);
      window.removeEventListener("resize", updatePlacement);
    };
  }, [open, monthYearPickerOpen]);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        if (monthYearPickerOpen) {
          setMonthYearPickerOpen(false);
        } else {
          setOpen(false);
        }
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open, monthYearPickerOpen]);

  function handleTextChange(nextValue: string) {
    onChange(formatDisplayDateInput(nextValue));
  }

  function handleSelect(date: Date | undefined) {
    if (!date) return;
    onChange(formatDate(date));
    onBlur?.();
    setOpen(false);
  }

  function handleVisibleMonthChange(month: Date) {
    setVisibleMonth(clampVisibleMonth(month));
  }

  function handleMonthYearSelect(month: Date) {
    setVisibleMonth(month);
    setMonthYearPickerOpen(false);
  }

  function toggleCalendar() {
    setOpen((current) => !current);
  }

  const borderClassName = error
    ? "border-red-500/70 focus-visible:ring-red-500/30"
    : inputClassName
      ? "border-white/10 focus-visible:border-[#14B8A6]/30"
      : "border-slate-300 dark:border-slate-700";

  const resolvedInputClassName = inputClassName ?? fieldClassName;

  return (
    <label className="block min-w-0">
      <div className={labelClassName}>{label}</div>
      <div ref={containerRef} className="relative">
        <input
          type="text"
          inputMode="numeric"
          autoComplete="off"
          value={value}
          placeholder={placeholder}
          maxLength={DISPLAY_DATE_MAX_LENGTH}
          onChange={(event) => handleTextChange(event.target.value)}
          onBlur={onBlur}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          aria-expanded={open}
          aria-haspopup="dialog"
          className={`${resolvedInputClassName} ${borderClassName} pr-11`}
        />
        <button
          type="button"
          onClick={toggleCalendar}
          aria-label={`Open calendar for ${label}`}
          aria-expanded={open}
          className={`absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 ${
            open ? "text-[#14B8A6]" : "text-slate-400 hover:text-[#14B8A6]"
          }`}
        >
          <Calendar className="h-4 w-4" />
        </button>

        {open ? (
          <div
            ref={popupRef}
            role="dialog"
            aria-label={`${label} calendar`}
            className={`insurance-day-picker-popup${
              placement === "above" ? " insurance-day-picker-popup--above" : ""
            }`}
          >
            {monthYearPickerOpen ? (
              <InsuranceMonthYearPicker
                visibleMonth={visibleMonth}
                onSelect={handleMonthYearSelect}
                onBack={() => setMonthYearPickerOpen(false)}
              />
            ) : (
              <div className="insurance-day-picker-view">
                <DayPicker
                  mode="single"
                  selected={selectedDate}
                  onSelect={handleSelect}
                  month={visibleMonth}
                  onMonthChange={handleVisibleMonthChange}
                  disabled={{ before: MIN_DATE, after: MAX_DATE }}
                  showOutsideDays
                  className="insurance-day-picker"
                  components={dayPickerComponents}
                  classNames={{
                    root: `${defaultClassNames.root} insurance-day-picker-root`,
                    months: `${defaultClassNames.months} insurance-day-picker-months`,
                    month: `${defaultClassNames.month} insurance-day-picker-month`,
                    month_caption: `${defaultClassNames.month_caption} insurance-day-picker-caption`,
                    caption_label: `${defaultClassNames.caption_label} insurance-day-picker-caption-label`,
                    nav: `${defaultClassNames.nav} insurance-day-picker-nav`,
                    button_previous: `${defaultClassNames.button_previous} insurance-day-picker-nav-btn`,
                    button_next: `${defaultClassNames.button_next} insurance-day-picker-nav-btn`,
                    weekdays: `${defaultClassNames.weekdays} insurance-day-picker-weekdays`,
                    weekday: `${defaultClassNames.weekday} insurance-day-picker-weekday`,
                    week: `${defaultClassNames.week} insurance-day-picker-week`,
                    day: `${defaultClassNames.day} insurance-day-picker-day`,
                    day_button: `${defaultClassNames.day_button} insurance-day-picker-day-btn`,
                    selected: `${defaultClassNames.selected} insurance-day-picker-selected`,
                    today: `${defaultClassNames.today} insurance-day-picker-today`,
                    outside: `${defaultClassNames.outside} insurance-day-picker-outside`,
                    disabled: `${defaultClassNames.disabled} insurance-day-picker-disabled`,
                  }}
                />
              </div>
            )}
          </div>
        ) : null}
      </div>
      {error ? (
        <p id={errorId} className="mt-1 text-sm text-red-400">
          {error}
        </p>
      ) : null}
    </label>
  );
}
