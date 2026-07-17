import {
  useEffect,
  useState,
  type ChangeEvent,
  type InputHTMLAttributes,
} from "react";

export function normalizeLeadingZeros(rawValue: string): string {
  const value = rawValue.trim();
  if (value === "") return "";
  return value.replace(/^0+(?=\d)/, "") || "0";
}

type SharedNumberInputProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "type" | "value" | "onChange"
> & {
  className?: string;
};

type RequiredNumberInputProps = SharedNumberInputProps & {
  value: number;
  onChange: (value: number) => void;
  allowEmpty?: false;
};

type OptionalNumberInputProps = SharedNumberInputProps & {
  value: number | null;
  onChange: (value: number | null) => void;
  /** When true, clearing the field commits `null` (e.g. Maximum Attempts). */
  allowEmpty: true;
};

export type NormalizedNumberInputProps = RequiredNumberInputProps | OptionalNumberInputProps;

function toDisplayValue(value: number | null | undefined): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

export function NormalizedNumberInput(props: NormalizedNumberInputProps) {
  const { value, onChange, allowEmpty = false, onBlur, ...inputProps } = props;
  const [displayValue, setDisplayValue] = useState(() => toDisplayValue(value));

  useEffect(() => {
    setDisplayValue(toDisplayValue(value));
  }, [value]);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextDisplay = normalizeLeadingZeros(event.target.value);
    setDisplayValue(nextDisplay);

    if (nextDisplay === "") {
      if (allowEmpty) {
        (onChange as (next: number | null) => void)(null);
      }
      return;
    }

    const numericValue = Number(nextDisplay);
    if (!Number.isFinite(numericValue)) return;
    onChange(numericValue as never);
  };

  return (
    <input
      {...inputProps}
      type="number"
      value={displayValue}
      onChange={handleChange}
      onBlur={(event) => {
        if (displayValue === "" && !allowEmpty) {
          setDisplayValue(toDisplayValue(value));
        }
        onBlur?.(event);
      }}
    />
  );
}
