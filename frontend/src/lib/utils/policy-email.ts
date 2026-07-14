const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const EMAIL_ERROR = "Please enter a valid email address";

export function validateEmail(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!EMAIL_PATTERN.test(trimmed)) {
    return EMAIL_ERROR;
  }
  return null;
}
