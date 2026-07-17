import React, { useRef, useState } from "react";
import { motion } from "framer-motion";
import { useParams, useNavigate } from "react-router-dom";
import { useGetPolicy, useRenewPolicy, useReminderConfigs, useUpdatePolicy } from "../../lib/api/hooks";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { apiClient } from "../../lib/api/client";
import { Loading } from "../../components/ui/Loading";
import { formatDate } from "../../lib/utils/formatDate";
import {
  isoDateFromDisplay,
  toDisplayDate,
  validateDisplayDate,
} from "../../lib/utils/date-display";
import { ErrorState } from "../../components/ui/ErrorState";
import { InsuranceDatePicker } from "../../components/ui/insurance-date-picker";
import { useToast } from "../../components/ui/toast";
import Combobox from "../../components/ui/Combobox";
import MultiSelect from "../../components/ui/MultiSelect";
import { RenewPolicyModal } from "../../components/insurance/RenewPolicyModal";
import type { InsurancePolicyCard } from "../../lib/api/types";
import {
  POLICY_DOCUMENT_ACCEPT,
  validatePolicyDocumentFile,
} from "../../lib/utils/policy-document";
import {
  normalizeMobileNumber,
  sanitizeMobileNumberInput,
  validateMobileNumber,
  MOBILE_NUMBER_MAX_INPUT_LENGTH,
  MOBILE_NUMBER_PLACEHOLDER,
} from "../../lib/utils/policy-mobile";
import { validateEmail } from "../../lib/utils/policy-email";
import { getPolicyMobile, getPolicyMobileValue, getPolicyEmailValue } from "../../lib/utils/policy-display";
import {
  formatRenewalFrequencyLabel,
  RENEWAL_FREQUENCY_DEFAULT,
  RENEWAL_FREQUENCY_OPTIONS,
  validateRenewalFrequency,
} from "../../lib/insurance/renewal-frequency";
import PersonalizedReminderBuilder from "../../components/insurance/PersonalizedReminderBuilder";
import {
  buildApiCustomRemindersPayload,
  computeCustomRemindersPreview,
  customRemindersFromPolicy,
  formatCustomReminderBeforeExpiryLabel,
  formatPreferredChannelsLabel,
  PREFERRED_CHANNEL_OPTIONS,
  validateDoNotDisturbWindow,
  validatePersonalizedReminders,
  type CustomReminderItem,
  type ReminderType,
} from "../../lib/insurance/custom-reminder-config";
import {
  customRemindersFromReminderConfigs,
  dndFromReminderConfigs,
  savePolicyReminderSettings,
} from "../../lib/insurance/reminder-settings-sync";

const STANDARD_CARRIERS = ["HDFC Ergo", "ICICI Lombard", "TATA AIG"] as const;
const STANDARD_POLICY_TYPES = ["Health", "Auto", "Life"] as const;

const fieldClassName =
  "w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 h-12 text-sm font-medium text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-400 placeholder:font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 focus-visible:border-[#14B8A6]/30 transition-colors";
const comboboxClassName =
  "h-12 w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-3 text-sm font-medium text-gray-800 dark:text-white hover:border-[#14B8A6]/40 transition-colors";
const formLabelClassName = "mb-2 block text-sm font-medium text-gray-800 dark:text-slate-300";

const documentButtonClassName =
  "inline-flex items-center rounded-xl border border-white/10 bg-slate-950/40 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-[#14B8A6]/40 hover:bg-[#14B8A6]/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40";

const labelClassName = "text-sm font-medium text-gray-600 dark:text-slate-500 sm:w-44 sm:shrink-0";
const valueClassName = "mt-1 text-base font-medium text-gray-800 dark:text-white sm:mt-0";
const detailRowClassName =
  "flex flex-col gap-1 border-b border-white/[0.06] py-3.5 last:border-b-0 sm:flex-row sm:items-center sm:gap-4";
const sectionTitleClassName =
  "mb-4 flex items-center gap-3 text-base font-bold tracking-tight text-black dark:text-white md:text-lg";

type EditForm = {
  policyholder_name: string;
  mobile_number: string;
  email: string;
  policy_number: string;
  policy_type: string;
  carrier: string;
  renewal_frequency: string;
  premium: string;
  expiry_date: string;
  preferred_channel: string[];
  reminder_type: ReminderType;
  dnd_start_time: string;
  dnd_end_time: string;
};

function sanitizeReminderType(value?: string | null): ReminderType {
  return value === "personalized" ? "personalized" : "default";
}

function formatReminderTypeLabel(value?: string | null): string {
  return sanitizeReminderType(value) === "personalized"
    ? "Custom"
    : "Organization default";
}

function StatusBadge({ status }: { status?: string | null }) {
  const s = (status || "").toLowerCase();
  const base = "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold";
  if (s === "active")
    return <span className={`${base} bg-[#14B8A6]/15 text-[#14B8A6] border-[#14B8A6]/25`}>Active</span>;
  if (s === "grace_period")
    return <span className={`${base} bg-amber-500/15 text-amber-300 border-amber-500/25`}>Grace Period</span>;
  if (s === "lapsed")
    return <span className={`${base} bg-red-500/15 text-red-300 border-red-500/25`}>Lapsed</span>;
  if (s === "pending")
    return <span className={`${base} bg-orange-500/15 text-orange-300 border-orange-500/25`}>Pending</span>;
  if (s.includes("renew"))
    return <span className={`${base} bg-emerald-500/15 text-emerald-300 border-emerald-500/25`}>Renewed</span>;
  return (
    <span className={`${base} bg-slate-500/15 text-slate-300 border-white/10`}>{status ?? "Unknown"}</span>
  );
}

function formatCurrency(value?: number | string | null) {
  if (value == null || value === "") return "-";
  const num = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(num)) return "-";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(num);
}

function expiryIsoFromValue(value?: string | null): string | null {
  if (!value) return null;
  const fromDisplay = isoDateFromDisplay(value);
  if (fromDisplay) {
    return new Date(`${fromDisplay}T12:00:00.000Z`).toISOString();
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

function normalizeDndTime(value?: string | null, fallback = "21:00"): string {
  if (!value) return fallback;
  return value.length >= 5 ? value.slice(0, 5) : value;
}

function normalizePreferredChannels(policy: InsurancePolicyCard): string[] {
  const raw = policy.preferred_channel as string[] | string | null | undefined;
  if (Array.isArray(raw) && raw.length > 0) {
    return raw.map((channel) => channel.trim().toLowerCase()).filter(Boolean);
  }
  if (typeof raw === "string" && raw.trim()) {
    return [raw.trim().toLowerCase()];
  }
  return [];
}

function policyToForm(policy: InsurancePolicyCard): EditForm {
  return {
    policyholder_name: policy.policyholder_name ?? "",
    mobile_number: getPolicyMobileValue(policy) ?? "",
    email: getPolicyEmailValue(policy) ?? "",
    policy_number: policy.policy_number ?? "",
    policy_type: policy.policy_type ?? "",
    carrier: policy.carrier ?? "",
    renewal_frequency: policy.renewal_frequency ?? RENEWAL_FREQUENCY_DEFAULT,
    premium: policy.premium != null && policy.premium !== "" ? String(policy.premium) : "",
    expiry_date: toDisplayDate(policy.expiry_date),
    preferred_channel: normalizePreferredChannels(policy),
    reminder_type: sanitizeReminderType(policy.reminder_type),
    dnd_start_time: normalizeDndTime(policy.dnd_start_time, "21:00"),
    dnd_end_time: normalizeDndTime(policy.dnd_end_time, "08:00"),
  };
}

export function PolicyDetailsPage() {
  const { policyId } = useParams();
  const id = policyId ? Number(policyId) : undefined;
  const navigate = useNavigate();
  const { organizationId } = useWorkbench();
  const query = useGetPolicy(id);
  const reminderConfigsQuery = useReminderConfigs(organizationId, "policy", id);
  const update = useUpdatePolicy(organizationId);
  const renew = useRenewPolicy(organizationId);
  const { showToast } = useToast();
  const documentFileInputRef = useRef<HTMLInputElement>(null);

  const [isEditing, setIsEditing] = useState(false);
  const [renewModalOpen, setRenewModalOpen] = useState(false);
  const [form, setForm] = useState<EditForm | null>(null);
  const [pendingDocumentFile, setPendingDocumentFile] = useState<File | null>(null);
  const [documentError, setDocumentError] = useState<string | null>(null);
  const [mobileError, setMobileError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [renewalFrequencyError, setRenewalFrequencyError] = useState<string | null>(null);
  const [expiryDateError, setExpiryDateError] = useState<string | null>(null);
  const [customReminders, setCustomReminders] = useState<CustomReminderItem[]>([]);
  const [remindersError, setRemindersError] = useState<string | null>(null);
  const [dndError, setDndError] = useState<string | null>(null);
  const [preferredChannelsError, setPreferredChannelsError] = useState<string | null>(null);
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (query.isLoading) return <Loading label="Loading policy..." />;
  if (query.isError) return <ErrorState message="Failed to load policy" />;
  if (!query.data || id == null) return <ErrorState message="Policy not found" />;

  const resolvedPolicyId = id;
  const p = query.data;
  const documentName = p.document_name?.trim() || null;
  const documentPath = p.document_path?.trim() || null;
  const displayMobileNumber = getPolicyMobile(p);
  const policyEmail = getPolicyEmailValue(p);
  const showRenewButton = (p.status || "").toLowerCase() !== "renewed";
  const loadedReminderConfigs = reminderConfigsQuery.data?.configs ?? [];
  const remindersFromConfigs = customRemindersFromReminderConfigs(loadedReminderConfigs);
  const viewCustomReminders =
    sanitizeReminderType(p.reminder_type) === "personalized"
      ? remindersFromConfigs.length > 0
        ? remindersFromConfigs
        : customRemindersFromPolicy(p)
      : [];
  const viewReminderPreview = computeCustomRemindersPreview(
    expiryIsoFromValue(p.expiry_date),
    viewCustomReminders
  );

  async function handleConfirmRenewal(payload: { newExpiryDate: string; renewalNotes: string }) {
    if (id == null) return;
    try {
      await renew.mutateAsync({
        policyId: resolvedPolicyId,
        newExpiryDate: payload.newExpiryDate,
        renewalNotes: payload.renewalNotes || null,
      });
      setRenewModalOpen(false);
      showToast("Policy renewed successfully.", "success");
      await query.refetch();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to renew policy";
      showToast(message, "error");
    }
  }

  function startEditing() {
    setError(null);
    setDocumentError(null);
    setMobileError(null);
    setEmailError(null);
    setRenewalFrequencyError(null);
    setExpiryDateError(null);
    setRemindersError(null);
    setDndError(null);
    setPendingDocumentFile(null);
    const nextForm = policyToForm(p);
    const dnd = dndFromReminderConfigs(loadedReminderConfigs);
    if (dnd.start) {
      nextForm.dnd_start_time = dnd.start;
    }
    if (dnd.end) {
      nextForm.dnd_end_time = dnd.end;
    }
    setForm(nextForm);
    setCustomReminders(
      remindersFromConfigs.length > 0 ? remindersFromConfigs : customRemindersFromPolicy(p)
    );
    setIsEditing(true);
  }

  function cancelEditing() {
    setIsEditing(false);
    setForm(null);
    setCustomReminders([]);
    setPendingDocumentFile(null);
    setDocumentError(null);
    setMobileError(null);
    setEmailError(null);
    setRenewalFrequencyError(null);
    setExpiryDateError(null);
    setRemindersError(null);
    setDndError(null);
    setError(null);
    if (documentFileInputRef.current) {
      documentFileInputRef.current.value = "";
    }
  }

  function handleDocumentFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setDocumentError(null);

    if (!file) {
      setPendingDocumentFile(null);
      return;
    }

    const validationError = validatePolicyDocumentFile(file);
    if (validationError) {
      setPendingDocumentFile(null);
      setDocumentError(validationError);
      event.target.value = "";
      return;
    }

    setPendingDocumentFile(file);
  }

  function openDocumentFilePicker() {
    documentFileInputRef.current?.click();
  }

  async function saveChanges(event: React.FormEvent) {
    event.preventDefault();
    if (!form) return;

    setError(null);
    setDocumentError(null);
    setMobileError(null);
    setEmailError(null);
    setRenewalFrequencyError(null);
    setExpiryDateError(null);
    setRemindersError(null);
    setDndError(null);
    setPreferredChannelsError(null);

    if (!form.policyholder_name.trim() || !form.policy_number.trim() || !form.expiry_date) {
      setError("Please provide policyholder name, policy number and expiry date.");
      return;
    }

    const expiryValidationError = validateDisplayDate(form.expiry_date);
    if (expiryValidationError) {
      setExpiryDateError(expiryValidationError);
      return;
    }

    const expiryIso = isoDateFromDisplay(form.expiry_date);
    if (!expiryIso) {
      setExpiryDateError("Please enter a valid expiry date.");
      return;
    }

    if (form.mobile_number.trim()) {
      const mobileValidationError = validateMobileNumber(form.mobile_number);
      if (mobileValidationError) {
        setMobileError(mobileValidationError);
        return;
      }
    }

    const emailValidationError = validateEmail(form.email);
    if (emailValidationError) {
      setEmailError(emailValidationError);
      return;
    }

    const renewalFrequencyValidationError = validateRenewalFrequency(form.renewal_frequency);
    if (renewalFrequencyValidationError) {
      setRenewalFrequencyError(renewalFrequencyValidationError);
      return;
    }

    if (form.preferred_channel.length === 0) {
      setPreferredChannelsError("Select at least one preferred reminder channel.");
      return;
    }

    if (form.reminder_type === "personalized") {
      const remindersValidationError = validatePersonalizedReminders(customReminders);
      if (remindersValidationError) {
        setRemindersError(remindersValidationError);
        return;
      }

      const windowError = validateDoNotDisturbWindow(form.dnd_start_time, form.dnd_end_time);
      if (windowError) {
        setDndError(windowError);
        return;
      }
    }

    let document_name = documentName;
    let document_path = documentPath;
    let documentUploaded = false;

    try {
      if (pendingDocumentFile) {
        setIsUploadingDocument(true);
        const uploaded = await apiClient.uploadPolicyDocument(pendingDocumentFile, resolvedPolicyId);
        document_name = uploaded.document_name;
        document_path = uploaded.document_path;
        documentUploaded = true;
        setIsUploadingDocument(false);
      }

      await update.mutateAsync({
        policyId: resolvedPolicyId,
        updates: {
          policyholder_name: form.policyholder_name.trim(),
          mobile_number: form.mobile_number.trim() ? normalizeMobileNumber(form.mobile_number) : null,
          email: form.email.trim() || null,
          policy_number: form.policy_number.trim(),
          policy_type: form.policy_type || null,
          carrier: form.carrier || null,
          renewal_frequency: form.renewal_frequency,
          premium: form.premium ? Number(form.premium) : null,
          expiry_date: new Date(`${expiryIso}T12:00:00.000Z`).toISOString(),
          preferred_channel: form.preferred_channel,
          reminder_type: form.reminder_type,
          custom_reminders:
            form.reminder_type === "personalized"
              ? buildApiCustomRemindersPayload(customReminders)
              : [],
          dnd_start_time: form.reminder_type === "personalized" ? form.dnd_start_time : null,
          dnd_end_time: form.reminder_type === "personalized" ? form.dnd_end_time : null,
          document_name,
          document_path,
        },
      });

      if (organizationId != null && form.reminder_type === "personalized") {
        await savePolicyReminderSettings({
          organizationId,
          policyId: resolvedPolicyId,
          reminderType: form.reminder_type,
          preferredChannels: form.preferred_channel,
          customReminders,
          policyType: form.policy_type || null,
          dndStart: form.dnd_start_time,
          dndEnd: form.dnd_end_time,
        });
      }

      setIsEditing(false);
      setForm(null);
      setCustomReminders([]);
      setPendingDocumentFile(null);
      if (documentFileInputRef.current) {
        documentFileInputRef.current.value = "";
      }
      await Promise.all([query.refetch(), reminderConfigsQuery.refetch()]);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to save policy changes";
      if (pendingDocumentFile && !documentUploaded) {
        setDocumentError(message);
      } else {
        setError(message);
      }
    } finally {
      setIsUploadingDocument(false);
    }
  }

  const isSaving = isUploadingDocument || update.isPending;

  return (
    <div className="relative pb-10">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-80 overflow-hidden" aria-hidden>
        <div className="absolute -right-16 top-0 h-64 w-64 rounded-full bg-[#8B5CF6]/15 blur-3xl" />
        <div className="absolute left-1/4 top-16 h-48 w-48 rounded-full bg-[#14B8A6]/10 blur-3xl" />
      </div>

      <div className="relative flex justify-center px-1">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="gyantra-glass-card w-full max-w-[820px] border border-white/[0.08] p-6 shadow-[0_8px_40px_rgba(0,0,0,0.45),0_0_32px_rgba(20,184,166,0.06)] md:p-8"
        >
        <div className="mb-6 border-b border-white/[0.08] pb-6">
          <div className="mb-4">
            <button
              type="button"
              onClick={() => navigate("/app/insurance/policies")}
              className="inline-flex items-center text-sm font-medium text-[#14B8A6] transition hover:text-[#2dd4bf] hover:underline"
            >
              <span className="mr-2">←</span>
              <span>Back to Policies</span>
            </button>
          </div>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-black dark:text-white md:text-3xl">
                {isEditing ? "Edit Policy" : "Policy Details"}
              </h1>
              <p className="mt-2 text-sm leading-relaxed text-gray-700 dark:text-slate-400 md:text-base">
                {isEditing ? "Update policy information and documents" : "Details for the selected policy"}
              </p>
            </div>
            {!isEditing ? (
              <div className="flex flex-wrap gap-2 shrink-0">
                <button type="button" onClick={startEditing} className="btn">
                  Edit Policy
                </button>
                {showRenewButton ? (
                  <button type="button" onClick={() => setRenewModalOpen(true)} className="btn">
                    Renew Policy
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>

        {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}

        {!isEditing ? (
          <>
            <div>
              <div className={detailRowClassName}>
                <div className={labelClassName}>Policyholder</div>
                <div className={valueClassName}>{p.policyholder_name}</div>
              </div>

              <div className={detailRowClassName}>
                <div className={labelClassName}>Mobile Number</div>
                <div className={valueClassName}>{displayMobileNumber}</div>
              </div>

              <div className={detailRowClassName}>
                <div className={labelClassName}>Email Address</div>
                <div className={valueClassName}>
                  {policyEmail ? (
                    <a href={`mailto:${policyEmail}`} className="text-[#14B8A6] hover:text-[#2dd4bf] hover:underline">
                      {policyEmail}
                    </a>
                  ) : (
                    "-"
                  )}
                </div>
              </div>

              <div className={detailRowClassName}>
                <div className={labelClassName}>Policy Number</div>
                <div className={valueClassName}>{p.policy_number}</div>
              </div>

              <div className={detailRowClassName}>
                <div className={labelClassName}>Policy Type</div>
                <div className={valueClassName}>{p.policy_type ?? "-"}</div>
              </div>

              <div className={detailRowClassName}>
                <div className={labelClassName}>Renewal Frequency</div>
                <div className={valueClassName}>{formatRenewalFrequencyLabel(p.renewal_frequency)}</div>
              </div>

              <div className={detailRowClassName}>
                <div className={labelClassName}>Policy Provider</div>
                <div className={valueClassName}>{p.carrier ?? "-"}</div>
              </div>

              <div className={detailRowClassName}>
                <div className={labelClassName}>Premium</div>
                <div className={valueClassName}>{formatCurrency(p.premium)}</div>
              </div>

              <div className={detailRowClassName}>
                <div className={labelClassName}>Expiry Date</div>
                <div className={valueClassName}>{formatDate(p.expiry_date)}</div>
              </div>

              <div className={detailRowClassName}>
                <div className={labelClassName}>Status</div>
                <div className={valueClassName}>
                  <StatusBadge status={p.status} />
                </div>
              </div>

              <div className={`${detailRowClassName} last:border-b-0`}>
                <div className={labelClassName}>Reminder Channels</div>
                <div className={valueClassName}>{formatPreferredChannelsLabel(p.preferred_channel)}</div>
              </div>
            </div>

            <div className="border-t border-white/[0.08] pt-6 mt-8">
              <h2 className={sectionTitleClassName}>
                <span className="inline-block h-4 w-1 shrink-0 rounded-full bg-[#14B8A6]" aria-hidden />
                Reminder Settings
              </h2>
              <div>
                <div className={detailRowClassName}>
                  <div className={labelClassName}>Reminder Configuration</div>
                  <div className={valueClassName}>{formatReminderTypeLabel(p.reminder_type)}</div>
                </div>
                {sanitizeReminderType(p.reminder_type) === "personalized" ? (
                  <>
                    <div className={detailRowClassName}>
                      <div className={labelClassName}>Configured Reminders</div>
                      <div className={valueClassName}>
                        {viewCustomReminders.length > 0 ? (
                          <ul className="space-y-1 text-sm font-normal text-slate-300">
                            {viewCustomReminders.map((item, index) => (
                              <li key={`${item.reminder_unit}-${item.reminder_value}-${index}`}>
                                • {formatCustomReminderBeforeExpiryLabel(item.reminder_unit, item.reminder_value)}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          "-"
                        )}
                      </div>
                    </div>
                    {viewReminderPreview.length > 0 ? (
                      <div className={detailRowClassName}>
                        <div className={labelClassName}>Reminder Preview</div>
                        <div className={valueClassName}>
                          <ul className="space-y-1 text-sm font-normal text-slate-300">
                            {viewReminderPreview.map((line) => (
                              <li key={`${line.label}-${line.previewDate}`}>
                                • {line.label} → {line.previewDate}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    ) : null}
                    <div className={detailRowClassName}>
                      <div className={labelClassName}>DND Start Time</div>
                      <div className={valueClassName}>{p.dnd_start_time ?? "-"}</div>
                    </div>
                    <div className={`${detailRowClassName} last:border-b-0`}>
                      <div className={labelClassName}>DND End Time</div>
                      <div className={valueClassName}>{p.dnd_end_time ?? "-"}</div>
                    </div>
                  </>
                ) : (
                  <p className="text-sm leading-relaxed text-slate-400">
                    This policy will use the organization&apos;s default reminder configuration.
                  </p>
                )}
              </div>
            </div>

            <div className="border-t border-white/[0.08] pt-6 mt-8">
              <h2 className={sectionTitleClassName}>
                <span className="inline-block h-4 w-1 shrink-0 rounded-full bg-[#14B8A6]" aria-hidden />
                Documents
              </h2>
              {documentName ? (
                <div className="space-y-3">
                  <div className="text-sm font-semibold text-white">📄 {documentName}</div>
                  {documentPath ? (
                    <button
                      type="button"
                      onClick={() => window.open(documentPath, "_blank")}
                      className={documentButtonClassName}
                    >
                      View Document
                    </button>
                  ) : null}
                </div>
              ) : (
                <p className="text-sm text-slate-400">No document uploaded</p>
              )}
            </div>
          </>
        ) : form ? (
          <form onSubmit={saveChanges} className="space-y-6">
            <div>
              <h3 className={sectionTitleClassName}>
                <span className="inline-block h-4 w-1 shrink-0 rounded-full bg-[#14B8A6]" aria-hidden />
                Policy Information
              </h3>
              <div className="space-y-4">
                <label className="block">
                  <div className={`${labelClassName} mb-2 sm:w-auto`}>Policyholder Name</div>
                  <input
                    value={form.policyholder_name}
                    onChange={(e) => setForm({ ...form, policyholder_name: e.target.value })}
                    className={fieldClassName}
                  />
                </label>

                <label className="block">
                  <div className={`${labelClassName} mb-2 sm:w-auto`}>Mobile Number</div>
                  <input
                    value={form.mobile_number}
                    onChange={(event) => {
                      setMobileError(null);
                      setForm({ ...form, mobile_number: sanitizeMobileNumberInput(event.target.value) });
                    }}
                    onBlur={() => {
                      if (!form.mobile_number) return;
                      setMobileError(validateMobileNumber(form.mobile_number));
                    }}
                    inputMode="tel"
                    maxLength={MOBILE_NUMBER_MAX_INPUT_LENGTH}
                    placeholder={MOBILE_NUMBER_PLACEHOLDER}
                    aria-invalid={mobileError ? true : undefined}
                    className={`${fieldClassName}${mobileError ? " border-red-500/70 focus-visible:ring-red-500/30" : ""}`}
                  />
                  {mobileError ? (
                    <p className="mt-2 text-sm text-red-400">{mobileError}</p>
                  ) : null}
                </label>

                <label className="block">
                  <div className={`${labelClassName} mb-2 sm:w-auto`}>Email Address</div>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(event) => {
                      setEmailError(null);
                      setForm({ ...form, email: event.target.value });
                    }}
                    onBlur={() => {
                      if (!form.email.trim()) return;
                      setEmailError(validateEmail(form.email));
                    }}
                    placeholder="Enter email address"
                    aria-invalid={emailError ? true : undefined}
                    className={`${fieldClassName}${emailError ? " border-red-500/70 focus-visible:ring-red-500/30" : ""}`}
                  />
                  {emailError ? (
                    <p className="mt-2 text-sm text-red-400">{emailError}</p>
                  ) : null}
                </label>

                <label className="block">
                  <div className={`${labelClassName} mb-2 sm:w-auto`}>Policy Number</div>
                  <input
                    value={form.policy_number}
                    onChange={(e) => setForm({ ...form, policy_number: e.target.value })}
                    className={fieldClassName}
                  />
                </label>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <label className="block">
                    <div className={`${labelClassName} mb-2 sm:w-auto`}>Policy Type</div>
                    <select
                      value={form.policy_type}
                      onChange={(e) => setForm({ ...form, policy_type: e.target.value })}
                      className={fieldClassName}
                    >
                      <option value="">Select type</option>
                      {form.policy_type && !STANDARD_POLICY_TYPES.includes(form.policy_type as (typeof STANDARD_POLICY_TYPES)[number]) ? (
                        <option value={form.policy_type}>{form.policy_type}</option>
                      ) : null}
                      <option value="Health">Health</option>
                      <option value="Auto">Auto</option>
                      <option value="Life">Life</option>
                    </select>
                  </label>
                  <label className="block">
                    <div className={`${labelClassName} mb-2 sm:w-auto`}>Policy Provider</div>
                    <select
                      value={form.carrier}
                      onChange={(e) => setForm({ ...form, carrier: e.target.value })}
                      className={fieldClassName}
                    >
                      <option value="">Select Policy Provider</option>
                      {form.carrier && !STANDARD_CARRIERS.includes(form.carrier as (typeof STANDARD_CARRIERS)[number]) ? (
                        <option value={form.carrier}>{form.carrier}</option>
                      ) : null}
                      <option value="HDFC Ergo">HDFC Ergo</option>
                      <option value="ICICI Lombard">ICICI Lombard</option>
                      <option value="TATA AIG">TATA AIG</option>
                    </select>
                  </label>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <label className="block">
                    <div className={`${labelClassName} mb-2 sm:w-auto`}>
                      Renewal Frequency <span className="text-red-400">*</span>
                    </div>
                    <Combobox
                      items={RENEWAL_FREQUENCY_OPTIONS}
                      value={form.renewal_frequency}
                      onChange={(value) => {
                        setRenewalFrequencyError(null);
                        setForm({ ...form, renewal_frequency: value ?? "" });
                      }}
                      onBlur={() => setRenewalFrequencyError(validateRenewalFrequency(form.renewal_frequency))}
                      placeholder="Select Frequency"
                      searchable={false}
                      aria-invalid={renewalFrequencyError ? true : undefined}
                      className={`${comboboxClassName}${renewalFrequencyError ? " border-red-500/70 focus-visible:ring-red-500/30" : ""}`}
                    />
                    {renewalFrequencyError ? (
                      <p className="mt-2 text-sm text-red-400">{renewalFrequencyError}</p>
                    ) : null}
                  </label>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <label className="block">
                    <div className={`${labelClassName} mb-2 sm:w-auto`}>Premium</div>
                    <input
                      type="number"
                      step="0.01"
                      value={form.premium}
                      onChange={(e) => setForm({ ...form, premium: e.target.value })}
                      className={fieldClassName}
                    />
                  </label>
                  <InsuranceDatePicker
                    label="Expiry Date"
                    value={form.expiry_date}
                    onChange={(expiry_date) => {
                      setExpiryDateError(null);
                      setForm({ ...form, expiry_date });
                    }}
                    onBlur={() => setExpiryDateError(validateDisplayDate(form.expiry_date))}
                    error={expiryDateError}
                    labelClassName={`${labelClassName} mb-2 sm:w-auto`}
                    inputClassName={fieldClassName}
                  />
                </div>

                <div className={detailRowClassName}>
                  <div className={labelClassName}>Status</div>
                  <div className={valueClassName}>
                    <StatusBadge status={p.status} />
                  </div>
                </div>
              </div>
            </div>

            <div className="border-t border-white/[0.08] pt-6">
              <h3 className={sectionTitleClassName}>
                <span className="inline-block h-4 w-1 shrink-0 rounded-full bg-[#14B8A6]" aria-hidden />
                Reminder Settings
              </h3>
              <div className="space-y-4">
                <div className="block">
                  <span className={formLabelClassName}>Reminder Channels</span>
                  <p className="mb-3 text-xs text-slate-500">Select one or more channels</p>
                  <div className="w-full max-w-md">
                    <MultiSelect
                      items={PREFERRED_CHANNEL_OPTIONS}
                      value={form.preferred_channel}
                      onChange={(channels) => {
                        setPreferredChannelsError(null);
                        setForm({ ...form, preferred_channel: channels });
                      }}
                    />
                  </div>
                  {preferredChannelsError ? (
                    <p className="mt-2 text-sm text-red-400">{preferredChannelsError}</p>
                  ) : null}
                </div>

                <label className="inline-flex cursor-pointer items-center gap-3 text-sm font-medium text-gray-800 dark:text-slate-200">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded accent-[#14B8A6]"
                    checked={form.reminder_type === "default"}
                    onChange={(event) => {
                      setRemindersError(null);
                      setDndError(null);
                      setForm({
                        ...form,
                        reminder_type: event.target.checked ? "default" : "personalized",
                      });
                    }}
                  />
                  Use Default Reminder Configuration
                </label>

                {form.reminder_type === "default" ? (
                  <p className="text-xs leading-relaxed text-slate-500">
                    This policy will use the organization&apos;s default reminder configuration.
                  </p>
                ) : (
                  <PersonalizedReminderBuilder
                    expiryDateIso={expiryIsoFromValue(form.expiry_date)}
                    customReminders={customReminders}
                    onCustomRemindersChange={(items) => {
                      setRemindersError(null);
                      setCustomReminders(items);
                    }}
                    dndStart={form.dnd_start_time}
                    dndEnd={form.dnd_end_time}
                    onDndStartChange={(value) => setForm({ ...form, dnd_start_time: value })}
                    onDndEndChange={(value) => setForm({ ...form, dnd_end_time: value })}
                    dndError={dndError}
                    onDndErrorClear={() => setDndError(null)}
                    remindersError={remindersError}
                    labelClassName={formLabelClassName}
                    fieldClassName={fieldClassName}
                    comboboxClassName={comboboxClassName}
                  />
                )}
              </div>
            </div>

            <div className="border-t border-white/[0.08] pt-6">
              <h3 className={sectionTitleClassName}>
                <span className="inline-block h-4 w-1 shrink-0 rounded-full bg-[#14B8A6]" aria-hidden />
                Documents
              </h3>
              <input
                ref={documentFileInputRef}
                type="file"
                accept={POLICY_DOCUMENT_ACCEPT}
                onChange={handleDocumentFileChange}
                className="hidden"
              />
              {documentName ? (
                <div className="space-y-3">
                  <div className="text-sm font-semibold text-white">📄 {documentName}</div>
                  <div className="flex flex-wrap gap-3">
                    {documentPath ? (
                      <button
                        type="button"
                        onClick={() => window.open(documentPath, "_blank")}
                        className={documentButtonClassName}
                      >
                        View Document
                      </button>
                    ) : null}
                    <button type="button" onClick={openDocumentFilePicker} className={documentButtonClassName}>
                      Replace Document
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-slate-400">No document uploaded</p>
                  <button type="button" onClick={openDocumentFilePicker} className={documentButtonClassName}>
                    Upload Document
                  </button>
                </div>
              )}
              {pendingDocumentFile ? (
                <div className="mt-3 flex items-center gap-2 text-sm text-emerald-400">
                  <span aria-hidden="true" className="font-semibold">✓</span>
                  <span className="truncate font-medium text-slate-200">{pendingDocumentFile.name}</span>
                </div>
              ) : null}
              {documentError ? <p className="mt-2 text-sm text-red-400">{documentError}</p> : null}
              <p className="mt-3 text-xs text-slate-500">Supported formats: PDF, JPG, JPEG, PNG</p>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-3 border-t border-white/[0.08] pt-8">
              {isUploadingDocument ? <Loading label="Uploading document..." /> : null}
              {!isUploadingDocument && update.isPending ? <Loading label="Saving changes..." /> : null}
              <button
                type="button"
                onClick={cancelEditing}
                disabled={isSaving}
                className="inline-flex items-center rounded-xl px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/5 hover:text-white disabled:opacity-60"
              >
                Cancel
              </button>
              <button className="btn" type="submit" disabled={isSaving}>
                Save Changes
              </button>
            </div>
          </form>
        ) : null}

        <RenewPolicyModal
          open={renewModalOpen}
          currentExpiryDate={p.expiry_date}
          isSubmitting={renew.isPending}
          onClose={() => setRenewModalOpen(false)}
          onConfirm={handleConfirmRenewal}
        />
        </motion.div>
      </div>
    </div>
  );
}

export default PolicyDetailsPage;
