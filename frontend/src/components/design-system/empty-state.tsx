import { GlassCard } from "./glass-card";

type EmptyStateProps = {
  message: string;
  title?: string;
};

export function EmptyState({ message, title }: EmptyStateProps) {
  return (
    <GlassCard className="p-6">
      {title ? <h3 className="mb-2 text-base font-semibold text-slate-900 dark:text-white">{title}</h3> : null}
      <p className="text-sm text-slate-600 dark:text-slate-400">{message}</p>
    </GlassCard>
  );
}
