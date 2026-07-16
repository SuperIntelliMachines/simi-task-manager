import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useWorkbench } from "../../app/providers/workbench-provider";
import { ClaimsReminderRuleDialog } from "../../components/claims/reminder-rule-dialog";
import { DashboardLayout, SectionCard } from "../../components/design-system";
import { PlatformDialog } from "../../components/platform/platform-dialog";
import { Button } from "../../components/ui/button";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState";
import { Loading } from "../../components/ui/Loading";
import { useToast } from "../../components/ui/toast";
import { apiClient } from "../../lib/api/client";
import { useReminderConfigs } from "../../lib/api/hooks";
import { CLAIMS_WORKSPACE_NAME } from "../../lib/claims/navigation";
import {
  CLAIMS_REMINDER_ENTITY_TYPE,
  CLAIMS_REMINDER_SETTINGS_ENTITY_ID,
  CLAIMS_REMINDER_TEMPLATE_KEY,
  formatOffsetSummary,
  getChannelOption,
  getRecipientLabel,
  loadClaimsRecipientMap,
  mapApiGroupToClaimsRule,
  mapClaimsFormToApiReminder,
  removeClaimsRecipient,
  ruleToFormValues,
  saveClaimsRecipient,
  type ClaimsReminderFormValues,
  type ClaimsReminderRuleView,
} from "../../lib/claims/reminder-settings";
import { useReminderModuleConfig } from "../../lib/reminder-management/hooks";
import { resolveTriggerLabel } from "../../lib/reminder-management/module-config";

export function ClaimsRemindersPage() {
  const { organizationId } = useWorkbench();
  const orgId = organizationId ?? null;
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const moduleConfigQuery = useReminderModuleConfig(CLAIMS_REMINDER_ENTITY_TYPE);
  const moduleConfig = moduleConfigQuery.data;

  const configsQuery = useReminderConfigs(
    orgId,
    CLAIMS_REMINDER_ENTITY_TYPE,
    CLAIMS_REMINDER_SETTINGS_ENTITY_ID
  );

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<"create" | "edit">("create");
  const [editingRule, setEditingRule] = useState<ClaimsReminderRuleView | null>(null);
  const [deleteRule, setDeleteRule] = useState<ClaimsReminderRuleView | null>(null);
  const [saving, setSaving] = useState(false);
  const [togglingId, setTogglingId] = useState<number | null>(null);
  /** Keep disabled rows visible after PATCH until the next successful refetch of actives. */
  const [hiddenActiveIds, setHiddenActiveIds] = useState<number[]>([]);
  const [disabledRules, setDisabledRules] = useState<ClaimsReminderRuleView[]>([]);

  const recipientMap = useMemo(
    () => (orgId != null ? loadClaimsRecipientMap(orgId) : {}),
    [orgId, configsQuery.dataUpdatedAt, disabledRules]
  );

  const rules: ClaimsReminderRuleView[] = useMemo(() => {
    const groups = configsQuery.data?.configs ?? [];
    const active = groups
      .filter((group) => !hiddenActiveIds.includes(group.config_id))
      .map((group) => mapApiGroupToClaimsRule(group, recipientMap, moduleConfig));

    const disabledNotInActive = disabledRules.filter(
      (rule) => !active.some((item) => item.configId === rule.configId)
    );

    return [...active, ...disabledNotInActive].sort((left, right) =>
      left.triggerLabel.localeCompare(right.triggerLabel)
    );
  }, [configsQuery.data?.configs, recipientMap, hiddenActiveIds, disabledRules, moduleConfig]);

  async function invalidate() {
    if (orgId == null) return;
    await queryClient.invalidateQueries({
      queryKey: ["reminder-configs", orgId, CLAIMS_REMINDER_ENTITY_TYPE, CLAIMS_REMINDER_SETTINGS_ENTITY_ID],
    });
  }

  function openCreate() {
    setDialogMode("create");
    setEditingRule(null);
    setDialogOpen(true);
  }

  function openEdit(rule: ClaimsReminderRuleView) {
    setDialogMode("edit");
    setEditingRule(rule);
    setDialogOpen(true);
  }

  function enrichRuleFromForm(
    configId: number,
    form: ClaimsReminderFormValues
  ): ClaimsReminderRuleView {
    const channel = getChannelOption(form.channelKey);
    return {
      configId,
      triggerKey: form.triggerKey,
      triggerKind: form.triggerKind,
      triggerLabel: resolveTriggerLabel(moduleConfig, form.triggerKey),
      direction: form.direction,
      offsetValue: form.offsetValue,
      offsetUnit: form.offsetUnit,
      channelKey: form.channelKey,
      channelLabel: channel.label,
      apiChannel: channel.apiChannel,
      recipientKey: form.recipientKey,
      recipientLabel: getRecipientLabel(form.recipientKey),
      enabled: form.enabled,
      repeatEnabled: form.repeatEnabled,
      repeatFrequencyValue: form.repeatFrequencyValue,
      repeatFrequencyUnit: form.repeatFrequencyUnit,
      maxAttempts: form.maxAttempts,
      stopCondition: form.stopCondition,
    };
  }

  async function persistEnabledReminders(
    nextForms: ClaimsReminderFormValues[],
    recipients: ClaimsReminderFormValues["recipientKey"][]
  ) {
    if (orgId == null) {
      throw new Error("Organization is not loaded.");
    }

    const enabledForms = nextForms.filter((form) => form.enabled);
    const response = await apiClient.saveReminderSettings({
      organization_id: orgId,
      entity_type: CLAIMS_REMINDER_ENTITY_TYPE,
      entity_id: CLAIMS_REMINDER_SETTINGS_ENTITY_ID,
      reminders: enabledForms.map((form) => mapClaimsFormToApiReminder(form)),
      template_key: CLAIMS_REMINDER_TEMPLATE_KEY,
      entity_label: "Claims Reminders",
    });

    const saved = response.configs ?? [];
    enabledForms.forEach((form, index) => {
      const api = mapClaimsFormToApiReminder(form);
      const match = saved.find(
        (row) =>
          row.anchor_key === api.anchor_key &&
          row.offset_direction === api.offset_direction &&
          row.offset_value === api.offset_value &&
          row.offset_unit === api.offset_unit &&
          row.channel === api.channels[0] &&
          row.is_active
      );
      if (match) {
        const recipientIndex = nextForms.findIndex((item) => item === form);
        saveClaimsRecipient(
          orgId,
          match.id,
          recipients[recipientIndex] ?? form.recipientKey
        );
      }
    });

    return response;
  }

  async function handleSave(form: ClaimsReminderFormValues) {
    if (orgId == null) {
      showToast("Organization is not loaded.", "error");
      return;
    }

    setSaving(true);
    try {
      if (dialogMode === "create") {
        const existingForms = rules.map(ruleToFormValues);
        const createForm = { ...form, enabled: true };
        const nextForms = [...existingForms.filter((item) => item.enabled), createForm];
        const recipients = [
          ...rules.filter((rule) => rule.enabled).map((rule) => rule.recipientKey),
          form.recipientKey,
        ];
        await persistEnabledReminders(nextForms, recipients);
        await invalidate();

        if (!form.enabled) {
          const refreshed = await apiClient.getReminderConfigs(
            orgId,
            CLAIMS_REMINDER_ENTITY_TYPE,
            CLAIMS_REMINDER_SETTINGS_ENTITY_ID
          );
          const api = mapClaimsFormToApiReminder(form);
          const created = refreshed.configs.find(
            (row) =>
              row.anchor_key === api.anchor_key &&
              row.offset_direction === api.offset_direction &&
              row.offset_value === api.offset_value &&
              row.offset_unit === api.offset_unit &&
              row.channels.includes(api.channels[0])
          );
          if (created) {
            await apiClient.updateReminderConfig(created.config_id, { is_active: false });
            saveClaimsRecipient(orgId, created.config_id, form.recipientKey);
            setDisabledRules((current) => [
              ...current.filter((item) => item.configId !== created.config_id),
              enrichRuleFromForm(created.config_id, form),
            ]);
            setHiddenActiveIds((current) =>
              current.includes(created.config_id) ? current : [...current, created.config_id]
            );
          }
        } else {
          setHiddenActiveIds([]);
        }
        showToast("Reminder created.", "success");
      } else if (editingRule) {
        const api = mapClaimsFormToApiReminder(form);
        await apiClient.updateReminderConfig(editingRule.configId, {
          channels: api.channels,
          offset_value: form.offsetValue,
          offset_unit: form.offsetUnit,
          anchor_type: form.triggerKind,
          anchor_key: form.triggerKey,
          offset_direction: form.direction,
          is_active: form.enabled,
          repeat_enabled: form.repeatEnabled,
          repeat_frequency_value: form.repeatEnabled ? form.repeatFrequencyValue : null,
          repeat_frequency_unit: form.repeatEnabled ? form.repeatFrequencyUnit : null,
          max_attempts: form.maxAttempts,
          stop_condition: form.stopCondition,
        });
        saveClaimsRecipient(orgId, editingRule.configId, form.recipientKey);
        const enriched = enrichRuleFromForm(editingRule.configId, form);
        if (form.enabled) {
          setDisabledRules((current) => current.filter((item) => item.configId !== editingRule.configId));
          setHiddenActiveIds((current) => current.filter((id) => id !== editingRule.configId));
        } else {
          setDisabledRules((current) => [
            ...current.filter((item) => item.configId !== editingRule.configId),
            enriched,
          ]);
          setHiddenActiveIds((current) =>
            current.includes(editingRule.configId) ? current : [...current, editingRule.configId]
          );
        }
        showToast("Reminder updated.", "success");
      }

      setDialogOpen(false);
      setEditingRule(null);
      await invalidate();
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Failed to save reminder.", "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleToggle(rule: ClaimsReminderRuleView) {
    if (orgId == null) return;
    const nextEnabled = !rule.enabled;
    setTogglingId(rule.configId);
    try {
      await apiClient.updateReminderConfig(rule.configId, { is_active: nextEnabled });
      if (nextEnabled) {
        setDisabledRules((current) => current.filter((item) => item.configId !== rule.configId));
        setHiddenActiveIds((current) => current.filter((id) => id !== rule.configId));
      } else {
        setDisabledRules((current) => [
          ...current.filter((item) => item.configId !== rule.configId),
          { ...rule, enabled: false },
        ]);
        setHiddenActiveIds((current) =>
          current.includes(rule.configId) ? current : [...current, rule.configId]
        );
      }
      showToast(nextEnabled ? "Reminder enabled." : "Reminder disabled.", "success");
      await invalidate();
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Failed to update reminder.", "error");
    } finally {
      setTogglingId(null);
    }
  }

  async function handleDelete() {
    if (!deleteRule || orgId == null) return;
    setSaving(true);
    try {
      await apiClient.deleteReminderConfig(deleteRule.configId);
      removeClaimsRecipient(orgId, deleteRule.configId);
      setDisabledRules((current) => current.filter((item) => item.configId !== deleteRule.configId));
      setHiddenActiveIds((current) => current.filter((id) => id !== deleteRule.configId));
      setDeleteRule(null);
      showToast("Reminder deleted.", "success");
      await invalidate();
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Failed to delete reminder.", "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <DashboardLayout>
      <SectionCard
        title="Reminder Settings"
        eyebrow={CLAIMS_WORKSPACE_NAME}
        action={
          <Button onClick={openCreate} disabled={orgId == null}>
            Create Reminder
          </Button>
        }
      >
        <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
          Define Claims workflow reminders. Timing and delivery map to the shared reminder engine
          automatically.
        </p>

        {configsQuery.isLoading || moduleConfigQuery.isLoading ? <Loading /> : null}
        {configsQuery.isError ? (
          <ErrorState message="Could not load Claims reminder settings." />
        ) : null}

        {!configsQuery.isLoading &&
        !moduleConfigQuery.isLoading &&
        !configsQuery.isError &&
        rules.length === 0 ? (
          <EmptyState
            title="No reminders yet"
            message="Create a reminder for a Claims workflow stage or date trigger from module metadata."
          />
        ) : null}

        {!configsQuery.isLoading && !configsQuery.isError && rules.length > 0 ? (
          <div className="overflow-hidden rounded-2xl border border-slate-200/80 dark:border-white/10">
            <table className="min-w-full divide-y divide-slate-200/80 text-left text-sm dark:divide-white/10">
              <thead className="bg-slate-50/80 dark:bg-slate-950/50">
                <tr className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-3">Trigger</th>
                  <th className="px-4 py-3">Timing</th>
                  <th className="px-4 py-3">Channel</th>
                  <th className="px-4 py-3">Recipient</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70 bg-white/40 dark:divide-white/10 dark:bg-slate-950/20">
                {rules.map((rule) => (
                  <tr key={rule.configId} className={!rule.enabled ? "opacity-60" : undefined}>
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">
                      {rule.triggerLabel}
                    </td>
                    <td className="px-4 py-3 capitalize text-slate-700 dark:text-slate-300">
                      {rule.direction} {formatOffsetSummary(rule.offsetValue, rule.offsetUnit)}
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{rule.channelLabel}</td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{rule.recipientLabel}</td>
                    <td className="px-4 py-3">
                      <label className="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded accent-[#14B8A6]"
                          checked={rule.enabled}
                          disabled={togglingId === rule.configId}
                          onChange={() => void handleToggle(rule)}
                        />
                        {rule.enabled ? "Enabled" : "Disabled"}
                      </label>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-3">
                        <button
                          type="button"
                          className="text-sm font-medium text-[#0f766e] hover:underline dark:text-[#2dd4bf]"
                          onClick={() => openEdit(rule)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="text-sm font-medium text-rose-500 hover:underline"
                          onClick={() => setDeleteRule(rule)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </SectionCard>

      <ClaimsReminderRuleDialog
        open={dialogOpen}
        mode={dialogMode}
        initialValues={editingRule ? ruleToFormValues(editingRule) : null}
        saving={saving}
        onClose={() => {
          if (saving) return;
          setDialogOpen(false);
          setEditingRule(null);
        }}
        onSave={(values) => void handleSave(values)}
      />

      <PlatformDialog
        open={Boolean(deleteRule)}
        title="Delete Reminder"
        description={
          deleteRule
            ? `Remove the “${deleteRule.triggerLabel}” reminder (${deleteRule.direction} ${formatOffsetSummary(deleteRule.offsetValue, deleteRule.offsetUnit)})?`
            : undefined
        }
        onClose={() => {
          if (saving) return;
          setDeleteRule(null);
        }}
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleteRule(null)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void handleDelete()} disabled={saving}>
              {saving ? "Deleting…" : "Delete"}
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600 dark:text-slate-400">
          This deactivates the reminder rule. You can create it again later if needed.
        </p>
      </PlatformDialog>
    </DashboardLayout>
  );
}
