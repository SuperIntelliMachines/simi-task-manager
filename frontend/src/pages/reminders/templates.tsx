import { useMemo, useState } from "react";

import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { PlatformDialog } from "../../components/platform/platform-dialog";
import { PlatformTable } from "../../components/platform/platform-table";
import { ActionMenu, EyeIcon } from "../../components/ui/ActionMenu";
import { Button } from "../../components/ui/button";
import { resolveApiErrorMessage } from "../../lib/api/errors";
import { getReminderChannelLabel } from "../../lib/reminders/channels";
import { rememberModuleLabel } from "../../lib/reminder-management/format";
import { useReminderModules, useReminderTemplates } from "../../lib/reminder-management/hooks";
import type { ReminderTemplate } from "../../lib/reminder-management/types";

/** Catalog templates from GET /reminders/templates (read-only). */
export function ReminderTemplatesPage() {
  const templatesQuery = useReminderTemplates();
  const modulesQuery = useReminderModules();
  const moduleOptions = modulesQuery.data ?? [];

  for (const option of moduleOptions) {
    rememberModuleLabel(option.value, option.label);
  }

  const [preview, setPreview] = useState<ReminderTemplate | null>(null);
  const rows = useMemo(() => templatesQuery.data ?? [], [templatesQuery.data]);

  return (
    <DashboardLayout>
      <SectionCard eyebrow="Reminder Management" title="Templates">
        <p className="mb-4 text-sm text-slate-400">
          Catalog templates from the reminder platform. Custom template CRUD is not available in this
          phase.
        </p>
        {templatesQuery.isLoading ? (
          <LoadingState label="Loading templates…" />
        ) : templatesQuery.isError ? (
          <p className="text-sm text-rose-300">
            {resolveApiErrorMessage(templatesQuery.error, "Failed to load templates.")}
          </p>
        ) : (
          <PlatformTable
            emptyMessage="No catalog templates available."
            columns={[
              { key: "name", label: "Template Name" },
              { key: "channel", label: "Channel" },
              { key: "module", label: "Module" },
              { key: "subject", label: "Subject" },
              { key: "actions", label: "Actions", className: "w-16 text-right" },
            ]}
            rows={rows.map((template) => ({
              id: template.id,
              cells: [
                template.name,
                getReminderChannelLabel(template.channel),
                template.module && template.module !== "any" ? String(template.module) : "Any",
                template.subject || "—",
                <div key="actions" className="flex justify-end">
                  <ActionMenu
                    items={[
                      {
                        id: "preview",
                        label: "Preview",
                        icon: <EyeIcon />,
                        onSelect: () => setPreview(template),
                      },
                    ]}
                  />
                </div>,
              ],
            }))}
          />
        )}
      </SectionCard>

      <PlatformDialog
        open={Boolean(preview)}
        onClose={() => setPreview(null)}
        title={preview?.name ?? "Preview"}
        description={preview ? getReminderChannelLabel(preview.channel) : undefined}
        size="lg"
        footer={
          <Button variant="outline" onClick={() => setPreview(null)}>
            Close
          </Button>
        }
      >
        {preview ? (
          <div className="space-y-3 text-sm">
            {preview.subject ? (
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">Subject</div>
                <div className="mt-1 font-medium text-slate-900 dark:text-white">{preview.subject}</div>
              </div>
            ) : null}
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-500">Body</div>
              <pre className="mt-2 whitespace-pre-wrap rounded-xl border border-white/10 bg-slate-950/40 p-4 text-slate-200">
                {preview.body}
              </pre>
            </div>
          </div>
        ) : null}
      </PlatformDialog>
    </DashboardLayout>
  );
}
