import { useMemo } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { DashboardCard } from "../components/workbench/dashboard-card";
import { Button } from "../components/ui/button";
import { useWorkbench } from "../app/providers/workbench-provider";
import {
  useChannelConnections,
  useNotificationPreferences,
  useSendChannelTestMessage,
  useUpdateNotificationPreference,
  useUpsertChannelConnection,
} from "../lib/api/hooks";

const channelSchema = z.object({
  providerReference: z.string().min(3, "Provider reference is required."),
  setting: z.string().min(3, "A channel setting is required."),
  testRecipient: z.string().min(3, "A test recipient is required."),
});

type ChannelFormValues = z.infer<typeof channelSchema>;

function ChannelCard({
  channel,
  defaultReference,
  defaultSetting,
  defaultRecipient,
  organizationId,
}: {
  channel: "telegram" | "whatsapp";
  defaultReference: string;
  defaultSetting: string;
  defaultRecipient: string;
  organizationId: number | null;
}) {
  const upsertMutation = useUpsertChannelConnection(organizationId);
  const testMutation = useSendChannelTestMessage(organizationId);
  const form = useForm<ChannelFormValues>({
    resolver: zodResolver(channelSchema),
    defaultValues: {
      providerReference: defaultReference,
      setting: defaultSetting,
      testRecipient: defaultRecipient,
    },
  });

  const handleSave = form.handleSubmit(async (values) => {
    if (organizationId == null) return;
    await upsertMutation.mutateAsync({
      organization_id: organizationId,
      channel,
      provider_reference: values.providerReference,
      status: "active",
      settings: channel === "telegram" ? { botToken: values.setting, testRecipient: values.testRecipient } : { phoneNumberId: values.setting, testRecipient: values.testRecipient },
    });
  });

  const handleTest = form.handleSubmit(async (values) => {
    if (organizationId == null) return;
    const saved = await upsertMutation.mutateAsync({
      organization_id: organizationId,
      channel,
      provider_reference: values.providerReference,
      status: "active",
      settings: channel === "telegram" ? { botToken: values.setting, testRecipient: values.testRecipient } : { phoneNumberId: values.setting, testRecipient: values.testRecipient },
    });
    await testMutation.mutateAsync({ connectionId: saved.id, recipient: values.testRecipient, text: `${channel} connection test` });
  });

  return (
    <div className="rounded-2xl bg-black/30 backdrop-blur-lg border border-white/10 p-5" data-testid={`${channel}-channel-card`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold capitalize text-white">{channel}</h3>
          <p className="text-sm text-slate-300">Connection card with placeholder provider credentials.</p>
        </div>
        <span className="rounded-full bg-slate-800/30 px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-slate-300">MVP</span>
      </div>
      <form className="mt-4 space-y-3">
        <label className="block text-sm text-slate-300">
          Provider Reference
          <input className="mt-2 w-full rounded-md border border-slate-700 bg-slate-900/50 text-white px-3 h-12 placeholder:text-slate-500 focus-visible:ring-2 focus-visible:ring-ring" {...form.register("providerReference")} />
          {form.formState.errors.providerReference ? <span className="mt-1 block text-xs text-rose-600">{form.formState.errors.providerReference.message}</span> : null}
        </label>
        <label className="block text-sm text-slate-300">
          {channel === "telegram" ? "Bot Token" : "Phone Number ID"}
          <input className="mt-2 w-full rounded-md border border-slate-700 bg-slate-900/50 text-white px-3 h-12 placeholder:text-slate-500 focus-visible:ring-2 focus-visible:ring-ring" {...form.register("setting")} />
          {form.formState.errors.setting ? <span className="mt-1 block text-xs text-rose-600">{form.formState.errors.setting.message}</span> : null}
        </label>
        <label className="block text-sm text-slate-300">
          Test Recipient
          <input className="mt-2 w-full rounded-md border border-slate-700 bg-slate-900/50 text-white px-3 h-12 placeholder:text-slate-500 focus-visible:ring-2 focus-visible:ring-ring" {...form.register("testRecipient")} />
          {form.formState.errors.testRecipient ? <span className="mt-1 block text-xs text-rose-600">{form.formState.errors.testRecipient.message}</span> : null}
        </label>
        <div className="flex gap-3">
          <Button type="button" onClick={() => void handleSave()}>
            Save Connection
          </Button>
          <Button type="button" variant="outline" onClick={() => void handleTest()}>
            Send Test Message
          </Button>
        </div>
        {upsertMutation.isSuccess ? <p className="text-sm text-emerald-400">Connection saved.</p> : null}
        {testMutation.isSuccess ? <p className="text-sm text-sky-300">Test message queued.</p> : null}
      </form>
    </div>
  );
}

export function ChannelsPage() {
  const { organizationId } = useWorkbench();
  const connectionsQuery = useChannelConnections(organizationId);
  const preferencesQuery = useNotificationPreferences(organizationId);
  const updatePreference = useUpdateNotificationPreference(organizationId);

  const telegram = useMemo(
    () => connectionsQuery.data?.find((item) => item.channel === "telegram"),
    [connectionsQuery.data]
  );
  const whatsapp = useMemo(
    () => connectionsQuery.data?.find((item) => item.channel === "whatsapp"),
    [connectionsQuery.data]
  );

  return (
    <div className="flex justify-center">
      <div className="w-full max-w-[1100px] bg-black/40 backdrop-blur-xl border border-white/10 rounded-3xl shadow-2xl p-6">
        <div className="space-y-6">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-sky-400">Channels</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Telegram and WhatsApp connection settings</h1>
            <p className="mt-1 text-sm text-slate-300">Manage outbound connections and contact delivery preferences</p>
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <DashboardCard title="Connection Cards" eyebrow="Outbound Channels">
              <div className="grid gap-4">
                <ChannelCard
                  channel="telegram"
                  organizationId={organizationId}
                  defaultReference={telegram?.provider_reference ?? ""}
                  defaultSetting={String(telegram?.settings.botToken ?? "")}
                  defaultRecipient={String(telegram?.settings.testRecipient ?? "")}
                />
                <ChannelCard
                  channel="whatsapp"
                  organizationId={organizationId}
                  defaultReference={whatsapp?.provider_reference ?? ""}
                  defaultSetting={String(whatsapp?.settings.phoneNumberId ?? "")}
                  defaultRecipient={String(whatsapp?.settings.testRecipient ?? "")}
                />
              </div>
            </DashboardCard>

            <DashboardCard title="Consent and Preferred Channel" eyebrow="Contact Delivery">
              <div className="space-y-3">
                {(preferencesQuery.data ?? []).map((preference) => (
                  <div key={preference.id} className="rounded-2xl bg-black/30 backdrop-blur-lg border border-white/10 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-white">Contact #{preference.contact_id}</p>
                        <p className="text-sm text-slate-300">Consent status: {preference.opt_out ? "Opted out" : "Opted in"}</p>
                      </div>
                      <select
                        aria-label={`Preferred channel ${preference.id}`}
                        className="rounded-2xl border border-white/10 bg-slate-900/30 px-3 py-2 text-sm text-white"
                        value={preference.preferred_channel}
                        onChange={(event) =>
                          updatePreference.mutate({
                            preferenceId: preference.id,
                            updates: { preferred_channel: event.target.value },
                          })
                        }
                      >
                        <option value="telegram">Telegram</option>
                        <option value="whatsapp">WhatsApp</option>
                      </select>
                    </div>
                  </div>
                ))}
              </div>
            </DashboardCard>
          </div>
        </div>
      </div>
    </div>
  );
}
