/**
 * Channel → recipient field requirements for Create Reminder.
 * Generic across modules — keys match reminder channel catalog, not vertical names.
 */

export type ReminderRecipientFieldKey = "phone" | "email" | "telegramChatId";

export type ReminderRecipientFieldSpec = {
  key: ReminderRecipientFieldKey;
  label: string;
  placeholder: string;
  inputType: "tel" | "email" | "text";
  required: boolean;
  /** Form column span hint (1 or 2). */
  colSpan?: 1 | 2;
};

/** Channels that share a single Phone Number field. */
const PHONE_CHANNELS = new Set(["sms", "whatsapp"]);

/**
 * Resolve which recipient inputs to show for the selected channels.
 * Deduplicates shared phone for SMS + WhatsApp. In-app needs no fields.
 */
export function resolveRecipientFieldsForChannels(
  channels: readonly string[]
): ReminderRecipientFieldSpec[] {
  const normalized = new Set(
    channels.map((channel) => channel.trim().toLowerCase()).filter(Boolean)
  );

  const fields: ReminderRecipientFieldSpec[] = [];

  const needsPhone = [...PHONE_CHANNELS].some((key) => normalized.has(key));
  if (needsPhone) {
    fields.push({
      key: "phone",
      label: "Phone Number *",
      placeholder: "e.g. 9876543210",
      inputType: "tel",
      required: true,
      colSpan: 1,
    });
  }

  if (normalized.has("email")) {
    fields.push({
      key: "email",
      label: "Email Address *",
      placeholder: "name@example.com",
      inputType: "email",
      required: true,
      colSpan: 2,
    });
  }

  if (normalized.has("telegram")) {
    fields.push({
      key: "telegramChatId",
      label: "Telegram Chat ID *",
      placeholder: "e.g. 123456789",
      inputType: "text",
      required: true,
      colSpan: 2,
    });
  }

  return fields;
}

export function channelsNeedRecipientFields(channels: readonly string[]): boolean {
  return resolveRecipientFieldsForChannels(channels).length > 0;
}

export type ReminderRecipientValues = {
  phone: string;
  email: string;
  telegramChatId: string;
};

/** Validate recipient values against selected channels. Returns an error message or null. */
export function validateReminderRecipients(
  channels: readonly string[],
  values: ReminderRecipientValues
): string | null {
  const fields = resolveRecipientFieldsForChannels(channels);
  for (const field of fields) {
    if (!field.required) continue;
    const raw =
      field.key === "phone"
        ? values.phone
        : field.key === "email"
          ? values.email
          : values.telegramChatId;
    if (!raw.trim()) {
      if (field.key === "phone") {
        return "Phone number is required when WhatsApp or SMS is selected.";
      }
      if (field.key === "email") {
        return "Email address is required when Email is selected.";
      }
      return "Telegram chat ID is required when Telegram is selected.";
    }
  }
  return null;
}
