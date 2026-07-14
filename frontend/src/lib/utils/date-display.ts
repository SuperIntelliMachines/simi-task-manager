import { formatDate } from "./formatDate";

const MIN_YEAR = 1900;
const MAX_YEAR = 2100;

export const DISPLAY_DATE_REGEX = /^(\d{2})-(\d{2})-(\d{4})$/;

export const DISPLAY_DATE_FORMAT_HINT = "Use DD-MM-YYYY format (e.g. 15-06-2026).";

export const DISPLAY_DATE_MAX_LENGTH = 10;
export const DISPLAY_DATE_INPUT_DIGIT_LIMIT = 8;

/** Format raw keyboard/paste input as DD-MM-YYYY while typing (max 8 digits). */
export function formatDisplayDateInput(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, DISPLAY_DATE_INPUT_DIGIT_LIMIT);
  if (digits.length <= 2) {
    return digits;
  }
  if (digits.length <= 4) {
    return `${digits.slice(0, 2)}-${digits.slice(2)}`;
  }
  return `${digits.slice(0, 2)}-${digits.slice(2, 4)}-${digits.slice(4)}`;
}

/** Format a Date or ISO value as DD-MM-YYYY. */
export function toDisplayDate(value: string | Date | null | undefined): string {
  return formatDate(value);
}

export function todayDisplayDate(): string {
  return toDisplayDate(new Date());
}

export function addDaysToDisplayDate(displayDate: string, days: number): string {
  const iso = isoDateFromDisplay(displayDate);
  if (!iso) return todayDisplayDate();
  const date = new Date(`${iso}T12:00:00.000Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return toDisplayDate(date);
}

/** Convert DD-MM-YYYY to YYYY-MM-DD for native date inputs and API helpers. */
export function isoDateFromDisplay(display: string | null | undefined): string | null {
  if (!display) return null;
  const trimmed = display.trim();
  const match = /^(\d{2})-(\d{2})-(\d{4})$/.exec(trimmed);
  if (!match) return null;

  const day = Number(match[1]);
  const month = Number(match[2]);
  const year = Number(match[3]);

  if (!isValidDisplayDateParts(day, month, year)) {
    return null;
  }

  return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

/** Convert YYYY-MM-DD from native date picker to DD-MM-YYYY. */
export function displayDateFromIso(isoDate: string | null | undefined): string | null {
  if (!isoDate) return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate.trim());
  if (!match) return null;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);

  if (!isValidDisplayDateParts(day, month, year)) {
    return null;
  }

  return `${String(day).padStart(2, "0")}-${String(month).padStart(2, "0")}-${String(year).padStart(4, "0")}`;
}

export function isValidDisplayDate(display: string | null | undefined): boolean {
  return isoDateFromDisplay(display) != null;
}

/** Return a user-facing validation error, or null when the date is valid. */
export function validateDisplayDate(display: string | null | undefined): string | null {
  if (!display || !display.trim()) {
    return `Please enter a date. ${DISPLAY_DATE_FORMAT_HINT}`;
  }

  const trimmed = display.trim();
  const partialMatch = /^(\d{2})-(\d{2})-(\d+)$/.exec(trimmed);
  if (partialMatch && partialMatch[3].length !== 4) {
    return "Year must be exactly 4 digits.";
  }

  if (!DISPLAY_DATE_REGEX.test(trimmed)) {
    return `Invalid date format. ${DISPLAY_DATE_FORMAT_HINT}`;
  }

  const match = DISPLAY_DATE_REGEX.exec(trimmed);
  if (!match) {
    return `Invalid date format. ${DISPLAY_DATE_FORMAT_HINT}`;
  }

  const day = Number(match[1]);
  const month = Number(match[2]);
  const year = Number(match[3]);

  if (year < MIN_YEAR || year > MAX_YEAR) {
    return `Year must be between ${MIN_YEAR} and ${MAX_YEAR}.`;
  }

  if (!isValidDisplayDateParts(day, month, year)) {
    return "Please enter a valid calendar date.";
  }

  return null;
}

function isValidDisplayDateParts(day: number, month: number, year: number): boolean {
  if (!Number.isInteger(day) || !Number.isInteger(month) || !Number.isInteger(year)) {
    return false;
  }
  if (year < MIN_YEAR || year > MAX_YEAR) {
    return false;
  }
  if (month < 1 || month > 12 || day < 1 || day > 31) {
    return false;
  }

  const date = new Date(Date.UTC(year, month - 1, day, 12, 0, 0, 0));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

export const DATE_PICKER_MIN_ISO = `${MIN_YEAR}-01-01`;
export const DATE_PICKER_MAX_ISO = `${MAX_YEAR}-12-31`;

export const RENEWAL_EXPIRY_MUST_BE_LATER_MESSAGE =
  "New expiry date must be later than the current expiry date.";

function isoDateFromAny(value: string | null | undefined): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;

  const fromDisplay = isoDateFromDisplay(trimmed);
  if (fromDisplay) return fromDisplay;

  const display = toDisplayDate(trimmed);
  const fromFormatted = isoDateFromDisplay(display);
  if (fromFormatted) return fromFormatted;

  const isoPrefix = /^(\d{4})-(\d{2})-(\d{2})/.exec(trimmed);
  if (isoPrefix) {
    return displayDateFromIso(`${isoPrefix[1]}-${isoPrefix[2]}-${isoPrefix[3]}`)
      ? `${isoPrefix[1]}-${isoPrefix[2]}-${isoPrefix[3]}`
      : null;
  }

  return null;
}

/** Validate renewal expiry: format, calendar date, and strictly after current expiry. */
export function validateRenewalExpiryDate(
  newExpiryDisplay: string | null | undefined,
  currentExpiryValue: string | null | undefined,
): string | null {
  const formatError = validateDisplayDate(newExpiryDisplay);
  if (formatError) {
    return formatError;
  }

  const newIso = isoDateFromDisplay(newExpiryDisplay!.trim());
  const currentIso = isoDateFromAny(currentExpiryValue);
  if (!newIso || !currentIso) {
    return "Please enter a valid calendar date.";
  }

  if (newIso <= currentIso) {
    return RENEWAL_EXPIRY_MUST_BE_LATER_MESSAGE;
  }

  return null;
}

export function isRenewalExpiryDateValid(
  newExpiryDisplay: string | null | undefined,
  currentExpiryValue: string | null | undefined,
): boolean {
  return validateRenewalExpiryDate(newExpiryDisplay, currentExpiryValue) == null;
}
