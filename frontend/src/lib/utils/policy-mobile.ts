export const MOBILE_NUMBER_PLACEHOLDER = "Enter mobile number (e.g. +919876543210)";
export const MOBILE_NUMBER_MAX_LENGTH = 15;
export const MOBILE_NUMBER_MAX_INPUT_LENGTH = 16;
export const MOBILE_NUMBER_MIN_LENGTH = 10;
export const MOBILE_NUMBER_ERROR = "Please enter a valid mobile number";

export function sanitizeMobileNumberInput(value: string): string {
  const compact = value.replace(/\s/g, "");
  if (compact.startsWith("+")) {
    const digits = compact.slice(1).replace(/\D/g, "").slice(0, MOBILE_NUMBER_MAX_LENGTH);
    return digits ? `+${digits}` : "+";
  }
  return compact.replace(/\D/g, "").slice(0, MOBILE_NUMBER_MAX_LENGTH);
}

export function normalizeMobileNumber(value: string): string {
  return sanitizeMobileNumberInput(value.trim());
}

export function validateMobileNumber(value: string): string | null {
  const compact = value.replace(/\s/g, "");
  if (!compact || compact === "+") {
    return MOBILE_NUMBER_ERROR;
  }
  const digits = compact.startsWith("+")
    ? compact.slice(1).replace(/\D/g, "")
    : compact.replace(/\D/g, "");
  if (digits.length < MOBILE_NUMBER_MIN_LENGTH || digits.length > MOBILE_NUMBER_MAX_LENGTH) {
    return MOBILE_NUMBER_ERROR;
  }
  if (!/^\+?[0-9]{10,15}$/.test(compact.startsWith("+") ? `+${digits}` : digits)) {
    return MOBILE_NUMBER_ERROR;
  }
  return null;
}
