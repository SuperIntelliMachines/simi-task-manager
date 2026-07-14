import type { PropsWithChildren, ReactNode } from "react";

import { GlassCard } from "./glass-card";

type ChartCardProps = PropsWithChildren<{
  title: string;
  description?: string;
  legend?: ReactNode;
  delay?: number;
}>;

export function ChartCard({ title, description, legend, delay = 0, children }: ChartCardProps) {
  return (
    <GlassCard delay={delay} className="p-6">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-lg font-bold text-black dark:text-foreground">{title}</h3>
          {description ? <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{description}</p> : null}
        </div>
        {legend}
      </div>
      {children}
    </GlassCard>
  );
}
