import { useEffect, useState } from "react";
import { useWorkbench } from "../../app/providers/workbench-provider";
import type { PolicyWithExtras } from "../../lib/utils/policy-display";
import { hasPolicyMobileNumber } from "../../lib/utils/policy-display";
import { formatLoggedInUserDisplayName } from "../../lib/utils/user-display";
import {
  getDefaultReminderChannel,
  hasPolicyEmail,
  openEmailReminder,
  openWhatsAppReminder,
  sendSmsReminder,
  type ReminderChannel,
} from "../../lib/utils/renewal-reminder";
type SendReminderDialogProps = {
  policy: PolicyWithExtras;
  open: boolean;
  onClose: () => void;
};

const CHANNEL_OPTIONS: Array<{ id: ReminderChannel; label: string }> = [
  { id: "whatsapp", label: "WhatsApp" },
  { id: "sms", label: "SMS" },
  { id: "email", label: "Email" },
];

function isChannelDisabled(policy: PolicyWithExtras, channel: ReminderChannel): boolean {
  if (channel === "email") {
    return !hasPolicyEmail(policy);
  }
  return !hasPolicyMobileNumber(policy);
}

export function SendReminderDialog({ policy, open, onClose }: SendReminderDialogProps) {
  const { currentUser } = useWorkbench();
  const loggedInUserName = formatLoggedInUserDisplayName(currentUser?.email);
  const [channel, setChannel] = useState<ReminderChannel>(() => getDefaultReminderChannel(policy));  const [notice, setNotice] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    if (!open) return;
    setChannel(getDefaultReminderChannel(policy));
    setNotice(null);
    setIsSending(false);
  }, [open, policy]);

  if (!open) return null;

  const selectedDisabled = isChannelDisabled(policy, channel);

  async function handleSend() {
    if (selectedDisabled || isSending) return;
    setNotice(null);

    if (channel === "whatsapp") {
      openWhatsAppReminder(policy, loggedInUserName);
      onClose();
      return;
    }

    if (channel === "email") {
      openEmailReminder(policy, loggedInUserName);
      onClose();
      return;
    }

    setIsSending(true);
    try {
      const result = await sendSmsReminder(policy, {
        loggedInUserName,
        actorUserId: currentUser?.id,
      });      if (result.sent) {
        onClose();
        return;
      }
      setNotice(result.message ?? "SMS integration coming soon.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="send-reminder-title"
        className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0b1220]/95 p-6 shadow-[0_20px_60px_-24px_rgba(2,6,23,0.8)]"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="send-reminder-title" className="text-lg font-semibold text-white">
          Choose Communication Channel
        </h2>

        <fieldset className="mt-5 space-y-3">
          {CHANNEL_OPTIONS.map((option) => {
            const disabled = isChannelDisabled(policy, option.id);
            return (
              <label
                key={option.id}
                className={`flex items-center gap-3 rounded-lg border px-4 py-3 transition ${
                  disabled
                    ? "cursor-not-allowed border-white/5 bg-white/3 opacity-50"
                    : channel === option.id
                      ? "cursor-pointer border-[#14B8A6]/40 bg-[#14B8A6]/10"
                      : "cursor-pointer border-white/10 bg-white/5 hover:border-white/20"
                }`}
              >
                <input
                  type="radio"
                  name="reminder-channel"
                  value={option.id}
                  checked={channel === option.id}
                  disabled={disabled}
                  onChange={() => {
                    setNotice(null);
                    setChannel(option.id);
                  }}
                  className="h-4 w-4 accent-[#14B8A6]"
                />
                <span className="text-sm font-medium text-slate-200">{option.label}</span>
              </label>
            );
          })}
        </fieldset>

        {notice ? <p className="mt-4 text-sm text-amber-400">{notice}</p> : null}

        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSending}
            className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-300 transition hover:bg-white/10 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSend}
            disabled={selectedDisabled || isSending}
            className="rounded-lg border border-[#14B8A6]/40 bg-[#14B8A6]/20 px-4 py-2 text-sm font-medium text-white transition hover:bg-[#14B8A6]/30 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSending ? "Sending…" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
