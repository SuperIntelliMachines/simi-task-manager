import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";

import {
  ReminderSchedulingFields,
  type ReminderSchedulingValues,
} from "./ReminderSchedulingFields";

const initialValues: ReminderSchedulingValues = {
  offsetValue: 30,
  offsetUnit: "days",
  offsetDirection: "before",
  repeatEnabled: true,
  repeatFrequencyValue: 1,
  repeatFrequencyUnit: "days",
  maxAttempts: null,
  stopCondition: "entity_ineligible",
};

function StatefulReminderSchedulingFields({
  onValuesChange,
}: {
  onValuesChange?: (values: ReminderSchedulingValues) => void;
}) {
  const [values, setValues] = useState(initialValues);

  return (
    <ReminderSchedulingFields
      value={values}
      onChange={(patch) => {
        setValues((current) => {
          const next = { ...current, ...patch };
          onValuesChange?.(next);
          return next;
        });
      }}
    />
  );
}

describe("ReminderSchedulingFields", () => {
  it("normalizes leading zeros across all scheduling numeric fields", () => {
    let latestValues = initialValues;
    render(<StatefulReminderSchedulingFields onValuesChange={(values) => (latestValues = values)} />);

    const offsetInput = screen.getByLabelText(/Offset Value/i);
    fireEvent.change(offsetInput, { target: { value: "024" } });
    expect(offsetInput).toHaveValue(24);
    expect(latestValues.offsetValue).toBe(24);
    expect(typeof latestValues.offsetValue).toBe("number");

    const repeatInput = screen.getByLabelText(/Repeat Every/i);
    fireEvent.change(repeatInput, { target: { value: "028" } });
    expect(repeatInput).toHaveValue(28);
    expect(latestValues.repeatFrequencyValue).toBe(28);
    expect(typeof latestValues.repeatFrequencyValue).toBe("number");

    const maxAttemptsInput = screen.getByLabelText(/Maximum Attempts/i);
    fireEvent.change(maxAttemptsInput, { target: { value: "005" } });
    expect(maxAttemptsInput).toHaveValue(5);
    expect(latestValues.maxAttempts).toBe(5);
    expect(typeof latestValues.maxAttempts).toBe("number");
  });

  it("allows offset zero and temporary empty editing without forcing null for required fields", () => {
    let latestValues = initialValues;
    render(<StatefulReminderSchedulingFields onValuesChange={(values) => (latestValues = values)} />);

    const offsetInput = screen.getByLabelText(/Offset Value/i);
    fireEvent.change(offsetInput, { target: { value: "0" } });
    expect(offsetInput).toHaveValue(0);
    expect(latestValues.offsetValue).toBe(0);

    fireEvent.change(offsetInput, { target: { value: "000" } });
    expect(offsetInput).toHaveValue(0);
    expect(latestValues.offsetValue).toBe(0);

    fireEvent.change(offsetInput, { target: { value: "" } });
    expect(offsetInput).toHaveValue(null);
    expect(latestValues.offsetValue).toBe(0);

    fireEvent.blur(offsetInput);
    expect(offsetInput).toHaveValue(0);
  });

  it("keeps maximum attempts optional empty as null", () => {
    let latestValues = initialValues;
    render(<StatefulReminderSchedulingFields onValuesChange={(values) => (latestValues = values)} />);

    const maxAttemptsInput = screen.getByLabelText(/Maximum Attempts/i);
    fireEvent.change(maxAttemptsInput, { target: { value: "3" } });
    expect(latestValues.maxAttempts).toBe(3);

    fireEvent.change(maxAttemptsInput, { target: { value: "" } });
    expect(maxAttemptsInput).toHaveValue(null);
    expect(latestValues.maxAttempts).toBeNull();
  });
});
