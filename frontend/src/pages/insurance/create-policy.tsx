import React, { useRef, useState } from "react";
import { motion } from "framer-motion";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useCreatePolicy } from "../../lib/api/hooks";
import { apiClient } from "../../lib/api/client";
import { Loading } from "../../components/ui/Loading";
import { ErrorState } from "../../components/ui/ErrorState";
import { useNavigate, useLocation } from "react-router-dom";
import { usePatchLead } from "../../lib/api/hooks";
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
import { InsuranceDatePicker } from "../../components/ui/insurance-date-picker";
import Combobox from "../../components/ui/Combobox";
import MultiSelect from "../../components/ui/MultiSelect";
import { isoDateFromDisplay, validateDisplayDate } from "../../lib/utils/date-display";
import { resolveCreatePolicyErrorMessage } from "../../lib/api/errors";
import { useToast } from "../../components/ui/toast";
import {
  RENEWAL_FREQUENCY_DEFAULT,
  RENEWAL_FREQUENCY_OPTIONS,
  validateRenewalFrequency,
} from "../../lib/insurance/renewal-frequency";
import PersonalizedReminderBuilder from "../../components/insurance/PersonalizedReminderBuilder";
import {
  buildApiCustomRemindersPayload,
  PREFERRED_CHANNEL_OPTIONS,
  validateDoNotDisturbWindow,
  validatePersonalizedReminders,
  type CustomReminderItem,
  type ReminderType,
} from "../../lib/insurance/custom-reminder-config";
import { savePolicyReminderSettings } from "../../lib/insurance/reminder-settings-sync";

const ORG_MISSING_MESSAGE =
  "Your organization could not be loaded. Please refresh the page and try again.";

const labelClassName = "mb-2 block text-sm font-medium text-gray-800 dark:text-slate-300";
const fieldClassName =
  "w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 h-12 text-sm font-medium text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-400 placeholder:font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 focus-visible:border-[#14B8A6]/30 transition-colors";
const comboboxClassName =
  "h-12 w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-3 text-sm font-medium text-gray-800 dark:text-white hover:border-[#14B8A6]/40 transition-colors";
const sectionHeadingClassName =
  "mb-5 flex items-center gap-3 text-base font-semibold tracking-tight text-slate-900 dark:text-white md:text-lg";

const POLICY_TYPE_OPTIONS = [
  { value: "Health", label: "Health" },
  { value: "Auto", label: "Auto" },
  { value: "Life", label: "Life" },
];

const POLICY_PROVIDER_OPTIONS = [
  { value: "HDFC Ergo", label: "HDFC Ergo" },
  { value: "ICICI Lombard", label: "ICICI Lombard" },
  { value: "TATA AIG", label: "TATA AIG" },
];

function FormSection({
  title,
  children,
  first = false,
}: {
  title: string;
  children: React.ReactNode;
  first?: boolean;
}) {
  return (
    <section className={first ? "" : "mt-8 border-t border-slate-300/60 dark:border-white/[0.08] pt-8"}>
      <h3 className={sectionHeadingClassName}>
        <span className="inline-block h-4 w-1 shrink-0 rounded-full bg-[#14B8A6]" aria-hidden />
        {title}
      </h3>
      {children}
    </section>
  );
}

export function CreatePolicyPage() {
  const { organizationId } = useWorkbench();
  const { showToast } = useToast();
  const create = useCreatePolicy(organizationId);
  const patchLead = usePatchLead();
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const qs = new URLSearchParams(location.search);
  const leadIdParam = qs.get("lead_id") || qs.get("leadId");
  const leadId = leadIdParam ? Number(leadIdParam) : undefined;
  const [form, setForm] = useState({
    policyholder_name: "",
    mobile_number: "",
    email: "",
    policy_type: "",
    carrier: "",
    renewal_frequency: RENEWAL_FREQUENCY_DEFAULT,
    policy_number: "",
    premium: "",
    expiry_date: "",
    assigned_agent_user_id: "",
    preferred_channel: [] as string[],
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentError, setDocumentError] = useState<string | null>(null);
  const [mobileError, setMobileError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [expiryDateError, setExpiryDateError] = useState<string | null>(null);
  const [renewalFrequencyError, setRenewalFrequencyError] = useState<string | null>(null);
  // Unchecked by default → policy-specific (personalized) custom reminders.
  const [reminderType, setReminderType] = useState<ReminderType>("personalized");
  const [customReminders, setCustomReminders] = useState<CustomReminderItem[]>([]);
  const [dndStart, setDndStart] = useState("21:00");
  const [dndEnd, setDndEnd] = useState("08:00");
  const [remindersError, setRemindersError] = useState<string | null>(null);
  const [dndError, setDndError] = useState<string | null>(null);
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);
  const [preferredChannelsError, setPreferredChannelsError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setDocumentError(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const validationError = validatePolicyDocumentFile(file);
    if (validationError) {
      setSelectedFile(null);
      setDocumentError(validationError);
      event.target.value = "";
      return;
    }

    setSelectedFile(file);
  }

  function handleMobileNumberChange(event: React.ChangeEvent<HTMLInputElement>) {
    setMobileError(null);
    setForm({ ...form, mobile_number: sanitizeMobileNumberInput(event.target.value) });
  }

  function handleEmailChange(event: React.ChangeEvent<HTMLInputElement>) {
    setEmailError(null);
    setForm({ ...form, email: event.target.value });
  }

  const expiryIsoForPreview = form.expiry_date ? isoDateFromDisplay(form.expiry_date) : null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setDocumentError(null);
    setMobileError(null);
    setEmailError(null);
    setExpiryDateError(null);
    setRenewalFrequencyError(null);
    setRemindersError(null);
    setDndError(null);

    if (!form.policyholder_name || !form.policy_number) {
      setError("Please provide policyholder name and policy number.");
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

    const mobileValidationError = validateMobileNumber(form.mobile_number);
    if (mobileValidationError) {
      setMobileError(mobileValidationError);
      return;
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

    if (organizationId == null) {
      setError(ORG_MISSING_MESSAGE);
      showToast(ORG_MISSING_MESSAGE, "error");
      return;
    }

    setPreferredChannelsError(null);

    if (form.preferred_channel.length === 0) {
      setPreferredChannelsError("Select at least one preferred reminder channel.");
      return;
    }

    if (reminderType === "personalized") {
      const remindersValidationError = validatePersonalizedReminders(customReminders);
      if (remindersValidationError) {
        setRemindersError(remindersValidationError);
        return;
      }

      const windowError = validateDoNotDisturbWindow(dndStart, dndEnd);
      if (windowError) {
        setDndError(windowError);
        return;
      }
    }

    let document_name: string | null = null;
    let document_path: string | null = null;
    let documentUploaded = false;

    try {
      if (selectedFile) {
        setIsUploadingDocument(true);
        const uploaded = await apiClient.uploadPolicyDocument(selectedFile);
        document_name = uploaded.document_name;
        document_path = uploaded.document_path;
        documentUploaded = true;
        setIsUploadingDocument(false);
      }

      const created = await create.mutateAsync({
        actor_user_id: null,
        policyholder_name: form.policyholder_name,
        mobile_number: normalizeMobileNumber(form.mobile_number),
        email: form.email.trim() || null,
        policy_number: form.policy_number,
        policy_type: form.policy_type || null,
        carrier: form.carrier || null,
        renewal_frequency: form.renewal_frequency,
        premium: form.premium ? Number(form.premium) : null,
        expiry_date: new Date(`${expiryIso}T12:00:00.000Z`).toISOString(),
        assigned_agent_user_id: form.assigned_agent_user_id ? Number(form.assigned_agent_user_id) : null,
        preferred_channel: form.preferred_channel,
        reminder_type: reminderType,
        custom_reminders:
          reminderType === "personalized" ? buildApiCustomRemindersPayload(customReminders) : undefined,
        dnd_start_time: reminderType === "personalized" ? dndStart : null,
        dnd_end_time: reminderType === "personalized" ? dndEnd : null,
        document_name,
        document_path,
      });

      // Only create per-policy reminder configs when using custom settings.
      // Default = org-level generic rules (no policy-specific configs).
      if (created?.id && reminderType === "personalized") {
        await savePolicyReminderSettings({
          organizationId,
          policyId: created.id,
          reminderType,
          preferredChannels: form.preferred_channel,
          customReminders,
          policyType: form.policy_type || null,
          dndStart: dndStart,
          dndEnd: dndEnd,
        });
      }

      if (leadId && created?.id) {
        try {
          await patchLead.mutateAsync({ leadId, updates: { status: "renewed", related_policy_id: created.id } });
        } catch {
          // ignore patch errors
        }
      }
      showToast("Policy holder saved successfully.", "success");
      navigate("/app/insurance/policies");
    } catch (e: unknown) {
      const message = resolveCreatePolicyErrorMessage(e);
      showToast(message, "error");
      if (selectedFile && !documentUploaded) {
        setDocumentError(message);
      } else {
        setError(message);
      }
    } finally {
      setIsUploadingDocument(false);
    }
  }

  const isSaving = isUploadingDocument || create.isPending;

  return (
    <div className="relative pb-10">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-80 overflow-hidden" aria-hidden>
        <div className="absolute -right-16 top-0 h-64 w-64 rounded-full bg-[#8B5CF6]/15 blur-3xl" />
        <div className="absolute left-1/4 top-16 h-48 w-48 rounded-full bg-[#14B8A6]/10 blur-3xl" />
      </div>

      <div className="relative mx-auto flex max-w-[860px] justify-center px-1">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="gyantra-glass-card w-full border border-slate-300/50 dark:border-white/[0.08] p-6 shadow-[0_8px_30px_rgba(15,23,42,0.08),0_0_24px_rgba(20,184,166,0.04)] dark:shadow-[0_8px_40px_rgba(0,0,0,0.45),0_0_32px_rgba(20,184,166,0.06)] md:p-8"
        >
          <header className="mb-8 border-b border-slate-300/60 dark:border-white/[0.08] pb-6">
            <h1 className="text-3xl font-extrabold tracking-tight text-black dark:text-white md:text-4xl">Add Policy Holder</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-400 md:text-base">
              Add a new policy holder and configure their coverage and reminder preferences.
            </p>
          </header>

          {error ? <ErrorState message={error} /> : null}
          {organizationId == null ? (
            <p className="mb-6 text-sm font-medium text-amber-400/90">
              Loading organization context… Save is disabled until your session is ready.
            </p>
          ) : null}

          <form onSubmit={submit} className="space-y-0">
            <FormSection title="Policy Information" first>
              <div className="space-y-4">
                <label className="block">
                  <span className={labelClassName}>Policyholder Name</span>
                  <input
                    value={form.policyholder_name}
                    onChange={(e) => setForm({ ...form, policyholder_name: e.target.value })}
                    placeholder="Policyholder name"
                    className={fieldClassName}
                  />
                </label>

                <label className="block">
                  <span className={labelClassName}>Mobile Number *</span>
                  <input
                    value={form.mobile_number}
                    onChange={handleMobileNumberChange}
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
                  <span className={labelClassName}>Email Address</span>
                  <input
                    type="email"
                    value={form.email}
                    onChange={handleEmailChange}
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
                  <span className={labelClassName}>Policy Number</span>
                  <input
                    value={form.policy_number}
                    onChange={(e) => setForm({ ...form, policy_number: e.target.value })}
                    placeholder="Policy number"
                    className={fieldClassName}
                  />
                </label>
              </div>
            </FormSection>

            <FormSection title="Coverage Details">
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <label className="block">
                    <span className={labelClassName}>Policy Type</span>
                    <Combobox
                      items={POLICY_TYPE_OPTIONS}
                      value={form.policy_type || null}
                      onChange={(value) => setForm({ ...form, policy_type: value ?? "" })}
                      placeholder="Select type"
                      searchable={false}
                      className={comboboxClassName}
                    />
                  </label>
                  <label className="block">
                    <span className={labelClassName}>Policy Provider</span>
                    <Combobox
                      items={POLICY_PROVIDER_OPTIONS}
                      value={form.carrier || null}
                      onChange={(value) => setForm({ ...form, carrier: value ?? "" })}
                      placeholder="Select Policy Provider"
                      searchable={false}
                      className={comboboxClassName}
                    />
                  </label>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <label className="block">
                    <span className={labelClassName}>
                      Renewal Frequency <span className="text-red-400">*</span>
                    </span>
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

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <label className="block">
                    <span className={labelClassName}>Premium</span>
                    <input
                      type="number"
                      step="0.01"
                      value={form.premium}
                      onChange={(e) => setForm({ ...form, premium: e.target.value })}
                      placeholder="Premium amount"
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
                    labelClassName={labelClassName}
                    inputClassName={fieldClassName}
                  />
                </div>
              </div>
            </FormSection>

            <FormSection title="Policy Document">
              <div className="space-y-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={POLICY_DOCUMENT_ACCEPT}
                  onChange={handleFileChange}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 py-2.5 text-sm font-medium text-slate-700 dark:text-slate-200 transition hover:border-[#14B8A6]/40 hover:bg-[#14B8A6]/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40"
                >
                  Choose File
                </button>
                {selectedFile ? (
                  <div className="flex items-center gap-2 text-sm text-emerald-400">
                    <span aria-hidden="true" className="font-semibold">✓</span>
                    <span className="truncate font-medium text-slate-800 dark:text-slate-200">{selectedFile.name}</span>
                  </div>
                ) : null}
                {documentError ? <p className="text-sm text-red-400">{documentError}</p> : null}
                <p className="text-xs text-slate-600 dark:text-slate-500">Supported formats: PDF, JPG, JPEG, PNG</p>
              </div>
            </FormSection>

            <FormSection title="Reminder Settings">
              <div className="space-y-4">
                <div className="block">
                  <span className={labelClassName}>Reminder Channels</span>
                  <p className="mb-3 text-xs text-slate-600 dark:text-slate-500">Select one or more channels</p>
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
                    checked={reminderType === "default"}
                    onChange={(event) => {
                      setRemindersError(null);
                      setDndError(null);
                      setReminderType(event.target.checked ? "default" : "personalized");
                    }}
                  />
                  Use Default Reminder Configuration
                </label>

                {reminderType === "default" ? (
                  <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-500">
                    This policy will use the organization&apos;s default reminder configuration.
                  </p>
                ) : (
                  <PersonalizedReminderBuilder
                    expiryDateIso={
                      expiryIsoForPreview
                        ? new Date(`${expiryIsoForPreview}T12:00:00.000Z`).toISOString()
                        : null
                    }
                    customReminders={customReminders}
                    onCustomRemindersChange={(items) => {
                      setRemindersError(null);
                      setCustomReminders(items);
                    }}
                    dndStart={dndStart}
                    dndEnd={dndEnd}
                    onDndStartChange={setDndStart}
                    onDndEndChange={setDndEnd}
                    dndError={dndError}
                    onDndErrorClear={() => setDndError(null)}
                    remindersError={remindersError}
                    labelClassName={labelClassName}
                    fieldClassName={fieldClassName}
                    comboboxClassName={comboboxClassName}
                  />
                )}
              </div>
            </FormSection>

            <div className="mt-8 flex flex-wrap items-center justify-end gap-3 border-t border-slate-300/60 dark:border-white/[0.08] pt-8">
              {isUploadingDocument ? <Loading label="Uploading document..." /> : null}
              {!isUploadingDocument && create.isPending ? <Loading label="Creating..." /> : null}
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="inline-flex items-center rounded-xl px-4 py-2.5 text-sm font-medium text-slate-700 dark:text-slate-300 transition hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white"
              >
                Cancel
              </button>
              <button className="btn" type="submit" disabled={isSaving || organizationId == null}>
                Save Policy Holder
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  );
}

export default CreatePolicyPage;
