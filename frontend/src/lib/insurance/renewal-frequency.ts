export const RENEWAL_FREQUENCY_MONTHLY = "monthly";
export const RENEWAL_FREQUENCY_QUARTERLY = "quarterly";
export const RENEWAL_FREQUENCY_HALF_YEARLY = "half_yearly";
export const RENEWAL_FREQUENCY_YEARLY = "yearly";

export const RENEWAL_FREQUENCY_DEFAULT = RENEWAL_FREQUENCY_YEARLY;

export type RenewalFrequencyValue =
  | typeof RENEWAL_FREQUENCY_MONTHLY
  | typeof RENEWAL_FREQUENCY_QUARTERLY
  | typeof RENEWAL_FREQUENCY_HALF_YEARLY
  | typeof RENEWAL_FREQUENCY_YEARLY;

export const RENEWAL_FREQUENCY_OPTIONS: Array<{ value: RenewalFrequencyValue; label: string }> = [
  { value: RENEWAL_FREQUENCY_MONTHLY, label: "Monthly" },
  { value: RENEWAL_FREQUENCY_QUARTERLY, label: "Quarterly" },
  { value: RENEWAL_FREQUENCY_HALF_YEARLY, label: "Half-Yearly" },
  { value: RENEWAL_FREQUENCY_YEARLY, label: "Yearly" },
];

export const RENEWAL_FREQUENCY_LABELS: Record<RenewalFrequencyValue, string> = {
  [RENEWAL_FREQUENCY_MONTHLY]: "Monthly",
  [RENEWAL_FREQUENCY_QUARTERLY]: "Quarterly",
  [RENEWAL_FREQUENCY_HALF_YEARLY]: "Half-Yearly",
  [RENEWAL_FREQUENCY_YEARLY]: "Yearly",
};

export function formatRenewalFrequencyLabel(value: string | null | undefined): string {
  if (!value || !value.trim()) {
    return RENEWAL_FREQUENCY_LABELS[RENEWAL_FREQUENCY_DEFAULT];
  }
  const normalized = value.trim().toLowerCase() as RenewalFrequencyValue;
  return RENEWAL_FREQUENCY_LABELS[normalized] ?? value;
}

export function validateRenewalFrequency(value: string): string | null {
  if (!value.trim()) {
    return "Please select a renewal frequency.";
  }
  const normalized = value.trim().toLowerCase();
  if (!RENEWAL_FREQUENCY_OPTIONS.some((option) => option.value === normalized)) {
    return "Please select a renewal frequency.";
  }
  return null;
}
