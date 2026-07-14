import React, { useState } from "react";
import { motion } from "framer-motion";
import { usePatchLead, useGetFollowup } from "../../lib/api/hooks";
import { Loading } from "../ui/Loading";
import Combobox from "../ui/Combobox";
import { formatDate } from "../../lib/utils/formatDate";
import { getFollowupCustomerName } from "../../lib/utils/followup-display";
import { LEAD_FOLLOWUP_ACTION_OPTIONS, LEAD_STATUS_TOAST, leadStatusLabel } from "../../lib/utils/followup-schedule";
import { useToast } from "../ui/toast";
import { FollowUpLaterModal } from "./FollowUpLaterModal";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../lib/api/client";

type LeadItem = {
  id: number;
  status?: string;
  followup_due_at?: string | null;
  related_policy_id?: number | null;
  related_policy?: { id: number } | null;
  contact_phone?: string | null;
  customer_phone?: string | null;
  phone?: string | null;
  policyType?: string | null;
  policy_type?: string | null;
};

const ACTION_COMBOBOX_CLASS =
  "h-12 w-36 shrink-0 rounded-xl border border-white/10 bg-slate-950/40 px-3 text-sm font-medium text-white hover:border-[#14B8A6]/40 transition-colors";

function followupStatusClassName(status: string): string {
  const normalized = status.toLowerCase();
  const base = "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold";
  if (normalized === "interested" || normalized === "renewed") {
    return `${base} bg-emerald-500/15 text-emerald-300 border-emerald-500/25`;
  }
  if (normalized === "not_interested") {
    return `${base} bg-red-500/15 text-red-300 border-red-500/25`;
  }
  if (normalized === "follow_up_later") {
    return `${base} bg-orange-500/15 text-orange-300 border-orange-500/25`;
  }
  if (normalized === "follow_up_pending" || normalized === "open") {
    return `${base} bg-[#14B8A6]/15 text-[#14B8A6] border-[#14B8A6]/25`;
  }
  return `${base} bg-slate-500/15 text-slate-300 border-white/10`;
}

export function FollowUpCard({ item, index = 0 }: { item: LeadItem; index?: number }) {
  const patch = usePatchLead();
  const { showToast } = useToast();
  const [laterModalOpen, setLaterModalOpen] = useState(false);

  const followupDetailQuery = useGetFollowup(item.id);
  const policyId = item.related_policy_id ?? item.related_policy?.id ?? null;
  const policyQuery = useQuery({
    queryKey: ["policy", policyId],
    queryFn: () => apiClient.getPolicy(policyId!),
    enabled: !!policyId,
  });

  const detail = followupDetailQuery.data ?? null;
  const displayItem = detail ?? item;
  const name = getFollowupCustomerName(displayItem);
  const phone =
    detail?.contact_phone ?? item.contact_phone ?? item.customer_phone ?? item.phone ?? null;
  const policyType =
    detail?.policyType ?? item.policyType ?? item.policy_type ?? policyQuery.data?.policy_type ?? null;
  const status = displayItem.status ?? item.status ?? "unknown";
  const statusLabel = leadStatusLabel(status);
  const dueAt = displayItem.followup_due_at ?? item.followup_due_at;

  async function applyStatusUpdate(statusValue: string, followupDueAt?: string) {
    try {
      const updates: { status: string; followup_due_at?: string } = { status: statusValue };
      if (followupDueAt) {
        updates.followup_due_at = followupDueAt;
      }
      await patch.mutateAsync({ leadId: item.id, updates });
      await followupDetailQuery.refetch();
      showToast(LEAD_STATUS_TOAST[statusValue] ?? "Lead updated successfully.", "success");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update lead.";
      showToast(message, "error");
      throw err;
    }
  }

  async function handleAction(value: string) {
    if (!value) return;
    if (value === "follow_up_later") {
      setLaterModalOpen(true);
      return;
    }
    await applyStatusUpdate(value);
  }

  async function handleFollowUpLaterConfirm(followupDueAtIso: string) {
    try {
      await applyStatusUpdate("follow_up_later", followupDueAtIso);
      setLaterModalOpen(false);
    } catch {
      // toast already shown
    }
  }

  const isBusy =
    patch.isPending || followupDetailQuery.isLoading || followupDetailQuery.isFetching || policyQuery.isLoading;

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: 0.35,
          delay: Math.min(index * 0.04, 0.24),
          ease: [0.22, 1, 0.36, 1],
        }}
        className="gyantra-glass-card rounded-[20px] border border-white/[0.08] p-5 shadow-[0_8px_32px_rgba(0,0,0,0.35),0_0_24px_rgba(20,184,166,0.04)] transition-all duration-300 hover:border-[#14B8A6]/20"
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1 space-y-2">
            <p className="truncate text-lg font-semibold tracking-tight text-white">{name}</p>
            {phone ? <p className="text-sm text-slate-400">Phone: {phone}</p> : null}
            {policyType ? <p className="text-sm text-slate-400">Policy: {policyType}</p> : null}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="text-sm text-slate-500">Status:</span>
              <span className={followupStatusClassName(status)}>{statusLabel}</span>
            </div>
            <p className="text-sm text-slate-400">
              Follow-up Date:{" "}
              <span className="font-medium text-slate-200">{dueAt ? formatDate(dueAt) : "TBD"}</span>
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-3 self-start sm:pt-1">
            <a
              className="inline-flex items-center text-sm font-semibold text-[#14B8A6] transition hover:text-[#2dd4bf] hover:underline"
              href={`/app/insurance/followups/${item.id}`}
            >
              View
            </a>

            <div>
              <label className="sr-only">Actions</label>
              <Combobox
                items={LEAD_FOLLOWUP_ACTION_OPTIONS}
                placeholder="Actions"
                onChange={(v) => {
                  if (v) void handleAction(v);
                }}
                className={ACTION_COMBOBOX_CLASS}
                searchable={false}
              />
            </div>
          </div>
        </div>

        {isBusy ? (
          <div className="mt-3 border-t border-white/[0.06] pt-3">
            <Loading label="Saving..." />
          </div>
        ) : null}
      </motion.div>

      <FollowUpLaterModal
        open={laterModalOpen}
        customerName={name}
        isSubmitting={patch.isPending}
        onClose={() => setLaterModalOpen(false)}
        onConfirm={handleFollowUpLaterConfirm}
      />
    </>
  );
}

export default FollowUpCard;
