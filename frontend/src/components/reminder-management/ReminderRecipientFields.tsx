import {
  fieldClassName,
  labelClassName,
} from "../../lib/reminder-management/constants";
import {
  resolveRecipientFieldsForChannels,
  type ReminderRecipientFieldKey,
  type ReminderRecipientValues,
} from "../../lib/reminder-management/recipient-fields";

type ReminderRecipientFieldsProps = {
  channels: readonly string[];
  values: ReminderRecipientValues;
  onChange: (patch: Partial<ReminderRecipientValues>) => void;
};

export function ReminderRecipientFields({
  channels,
  values,
  onChange,
}: ReminderRecipientFieldsProps) {
  const fields = resolveRecipientFieldsForChannels(channels);
  if (fields.length === 0) return null;

  function fieldValue(key: ReminderRecipientFieldKey): string {
    if (key === "phone") return values.phone;
    if (key === "email") return values.email;
    return values.telegramChatId;
  }

  function setField(key: ReminderRecipientFieldKey, next: string) {
    if (key === "phone") onChange({ phone: next });
    else if (key === "email") onChange({ email: next });
    else onChange({ telegramChatId: next });
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {fields.map((field) => (
        <label
          key={field.key}
          className={`block min-w-0 ${field.colSpan === 2 ? "sm:col-span-2" : ""}`}
        >
          <span className={labelClassName}>{field.label}</span>
          <input
            type={field.inputType}
            className={fieldClassName}
            value={fieldValue(field.key)}
            onChange={(event) => setField(field.key, event.target.value)}
            placeholder={field.placeholder}
            autoComplete="off"
          />
        </label>
      ))}
    </div>
  );
}
