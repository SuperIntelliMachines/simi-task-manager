import type { PropsWithChildren, ReactNode } from "react";

import { GlassCard } from "./glass-card";

type SectionCardProps = PropsWithChildren<{
  title: string;
  eyebrow?: string;
  action?: ReactNode;
  delay?: number;
  className?: string;
}>;

export function SectionCard({ title, eyebrow, action, delay = 0, className = "", children }: SectionCardProps) {
  return (
    <GlassCard delay={delay} className={`p-6 ${className}`}>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          {eyebrow ? (
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#14B8A6]">{eyebrow}</p>
          ) : null}
          <h2 className={`${eyebrow ? "mt-2" : ""} text-xl font-semibold text-slate-900 dark:text-white`}>
            {title}
          </h2>
        </div>
        {action}
      </div>
      {children}
    </GlassCard>
  );
}

/** @deprecated Use SectionCard — kept for backward compatibility */
export function DashboardCard(props: SectionCardProps) {
  return <SectionCard {...props} />;
}
