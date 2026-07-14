import { useMemo, useState, type ReactNode } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useGetFollowup, usePatchLead } from "../../lib/api/hooks";
import { Loading } from "../../components/ui/Loading";
import { ErrorState } from "../../components/ui/ErrorState";
import { GlassCard } from "../../components/insurance/glass-card";
import { FollowUpLaterModal } from "../../components/insurance/FollowUpLaterModal";
import { Phone } from "../../components/insurance/icons";
import { formatDate } from "../../lib/utils/formatDate";
import { getFollowupCustomerName } from "../../lib/utils/followup-display";
import { LEAD_STATUS_TOAST, leadStatusLabel } from "../../lib/utils/followup-schedule";
import { useToast } from "../../components/ui/toast";

function display(value: string | number | null | undefined): string {
  if (value == null || value === "") return "N/A";
  return String(value);
}

function displayPolicyType(value: string | null | undefined): string {
  if (value == null || value === "") return "Not Converted Yet";
  return value;
}

function formatDateOrNa(value: string | null | undefined): string {
  if (!value) return "N/A";
  const formatted = formatDate(value);
  return formatted || "N/A";
}

const STATUS_STYLES: Record<string, { label: string; bg: string; text: string; border: string }> = {
  follow_up_pending: { label: "Pending", bg: "rgba(249,115,22,0.15)", text: "#FB923C", border: "rgba(249,115,22,0.35)" },
  open: { label: "Open", bg: "rgba(59,130,246,0.15)", text: "#60A5FA", border: "rgba(59,130,246,0.35)" },
  interested: { label: "Interested", bg: "rgba(20,184,166,0.15)", text: "#14B8A6", border: "rgba(20,184,166,0.35)" },
  renewed: { label: "Renewed", bg: "rgba(34,197,94,0.15)", text: "#4ADE80", border: "rgba(34,197,94,0.35)" },
  not_interested: { label: "Not Interested", bg: "rgba(239,68,68,0.15)", text: "#F87171", border: "rgba(239,68,68,0.35)" },
  follow_up_later: { label: "Follow-up Later", bg: "rgba(139,92,246,0.15)", text: "#C4B5FD", border: "rgba(139,92,246,0.35)" },
};

function StatusBadge({ status }: { status?: string | null }) {
  const key = (status || "").toLowerCase();
  const style = STATUS_STYLES[key] ?? {
    label: display(status),
    bg: "rgba(148,163,184,0.15)",
    text: "#94A3B8",
    border: "rgba(148,163,184,0.35)",
  };
  return (
    <span
      className="inline-flex rounded-full px-3 py-1 text-xs font-semibold"
      style={{ background: style.bg, color: style.text, border: `1px solid ${style.border}` }}
    >
      {style.label}
    </span>
  );
}

type DetailRowProps = { label: string; value: string; href?: string };

function DetailRow({ label, value, href }: DetailRowProps) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-sm font-semibold text-white sm:text-right">
        {href && value !== "N/A" ? (
          <a href={href} className="text-[#14B8A6] transition hover:text-[#5EEAD4]">
            {value}
          </a>
        ) : (
          value
        )}
      </dd>
    </div>
  );
}

function SectionCard({
  title,
  icon,
  delay,
  children,
}: {
  title: string;
  icon?: ReactNode;
  delay?: number;
  children: ReactNode;
}) {
  return (
    <GlassCard delay={delay} className="p-5 md:p-6">
      <div className="mb-4 flex items-center gap-2 border-b border-white/6 pb-3">
        {icon ? (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#14B8A6]/15 text-[#14B8A6]">
            {icon}
          </div>
        ) : null}
        <h2 className="text-base font-semibold text-white">{title}</h2>
      </div>
      <dl className="space-y-4">{children}</dl>
    </GlassCard>
  );
}

export function LeadDetailsPage() {
  const { followupId } = useParams();
  const id = followupId ? Number(followupId) : undefined;
  const q = useGetFollowup(id);
  const patch = usePatchLead();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [laterModalOpen, setLaterModalOpen] = useState(false);

  const item: any = q.data;

  const customerName = useMemo(() => getFollowupCustomerName(item), [item]);
  const phone = item?.contact_phone ?? item?.phone ?? null;
  const email = item?.email ?? item?.contact_email ?? null;
  const policyType = item?.policyType ?? item?.policy_type ?? null;

  if (q.isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Loading label="Loading lead details..." />
      </div>
    );
  }
  if (q.isError || !item) {
    return <ErrorState message="Lead not found" />;
  }

  async function markNotInterested() {
    try {
      await patch.mutateAsync({ leadId: item.id, updates: { status: "not_interested" } });
      await q.refetch();
      showToast(LEAD_STATUS_TOAST.not_interested, "success");
      navigate("/app/insurance/followups");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to update lead.", "error");
    }
  }

  async function handleFollowUpLaterConfirm(followupDueAtIso: string) {
    try {
      await patch.mutateAsync({
        leadId: item.id,
        updates: { status: "follow_up_later", followup_due_at: followupDueAtIso },
      });
      await q.refetch();
      setLaterModalOpen(false);
      showToast(LEAD_STATUS_TOAST.follow_up_later, "success");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to reschedule follow-up.", "error");
    }
  }

  function openFollowUpLaterModal() {
    setLaterModalOpen(true);
  }

  function convertToPolicy() {
    navigate(`/app/insurance/policies/create?lead_id=${item.id}`);
  }

  const notes = item.notes?.trim() ? item.notes : null;
  const isBusy = patch.isPending;

  return (
    <div className="mx-auto max-w-4xl space-y-5 pb-8">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
        <button
          type="button"
          onClick={() => navigate("/app/insurance/followups")}
          className="inline-flex items-center gap-2 rounded-lg border border-white/8 bg-white/5 px-3 py-2 text-sm font-medium text-slate-300 transition hover:border-[#14B8A6]/40 hover:bg-[#14B8A6]/10 hover:text-white"
        >
          <span aria-hidden>←</span>
          Back to Follow-up List
        </button>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.05 }}
        className="flex flex-wrap items-start justify-between gap-4"
      >
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#14B8A6]">Lead Follow-up</p>
          <h1 className="mt-1 text-2xl font-bold text-white md:text-3xl">{customerName}</h1>
          <p className="mt-2 text-sm text-slate-400">Review customer details and update follow-up status</p>
        </div>
        <StatusBadge status={item.status} />
      </motion.div>

      <div className="grid gap-4 md:grid-cols-2">
        <SectionCard title="Customer Information" delay={0.1} icon={<Phone className="h-4 w-4" />}>
          <DetailRow label="Customer Name" value={display(customerName === "Unnamed Customer" ? null : customerName)} />
          <DetailRow
            label="Phone Number"
            value={display(phone)}
            href={phone ? `tel:${String(phone).replace(/\s/g, "")}` : undefined}
          />
          <DetailRow
            label="Email"
            value={display(email)}
            href={email ? `mailto:${email}` : undefined}
          />
          <DetailRow label="Policy Type" value={displayPolicyType(policyType)} />
        </SectionCard>

        <SectionCard title="Follow-up Information" delay={0.15}>
          <DetailRow label="Follow-up Date" value={formatDateOrNa(item.followup_due_at)} />
          <DetailRow label="Created Date" value={formatDateOrNa(item.created_at)} />
          <DetailRow label="Status" value={leadStatusLabel(item.status)} />
          <DetailRow label="Preferred Channel" value={display(item.preferred_channel)} />
        </SectionCard>
      </div>

      <GlassCard delay={0.2} className="p-5 md:p-6">
        <h2 className="mb-4 border-b border-white/6 pb-3 text-base font-semibold text-white">Notes</h2>
        <div className="rounded-xl border border-white/6 bg-white/3 p-4">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
            {notes ?? "N/A"}
          </p>
        </div>
      </GlassCard>

      <GlassCard delay={0.25} className="p-5 md:p-6">
        <h2 className="mb-4 text-base font-semibold text-white">Actions</h2>
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
          <button
            type="button"
            disabled={isBusy}
            onClick={convertToPolicy}
            className="inline-flex flex-1 items-center justify-center rounded-xl border border-[#14B8A6]/40 bg-[#14B8A6]/15 px-4 py-3 text-sm font-semibold text-[#14B8A6] transition hover:bg-[#14B8A6]/25 disabled:opacity-50 sm:min-w-[160px] sm:flex-none"
          >
            Convert to Policy
          </button>
          <button
            type="button"
            disabled={isBusy}
            onClick={openFollowUpLaterModal}
            className="inline-flex flex-1 items-center justify-center rounded-xl border border-[#8B5CF6]/40 bg-[#8B5CF6]/15 px-4 py-3 text-sm font-semibold text-[#C4B5FD] transition hover:bg-[#8B5CF6]/25 disabled:opacity-50 sm:min-w-[160px] sm:flex-none"
          >
            Follow-up Later
          </button>
          <button
            type="button"
            disabled={isBusy}
            onClick={markNotInterested}
            className="inline-flex flex-1 items-center justify-center rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm font-semibold text-red-400 transition hover:bg-red-500/20 disabled:opacity-50 sm:min-w-[160px] sm:flex-none"
          >
            Mark Not Interested
          </button>
        </div>
      </GlassCard>

      <FollowUpLaterModal
        open={laterModalOpen}
        customerName={customerName}
        isSubmitting={patch.isPending}
        onClose={() => setLaterModalOpen(false)}
        onConfirm={handleFollowUpLaterConfirm}
      />
    </div>
  );
}

export default LeadDetailsPage;
