import type { PropsWithChildren, ReactNode } from "react";

type KpiGridProps = PropsWithChildren<{
  title?: string;
  columns?: "2" | "3" | "4";
}>;

const columnClass: Record<NonNullable<KpiGridProps["columns"]>, string> = {
  "2": "sm:grid-cols-2",
  "3": "sm:grid-cols-2 lg:grid-cols-3",
  "4": "sm:grid-cols-2 lg:grid-cols-4",
};

export function KpiGrid({ title, columns = "4", children }: KpiGridProps) {
  return (
    <section className="space-y-4">
      {title ? <h3 className="text-lg font-bold text-black dark:text-foreground">{title}</h3> : null}
      <div className={`grid grid-cols-1 gap-4 ${columnClass[columns]}`}>{children}</div>
    </section>
  );
}

export function KpiGridItem({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
