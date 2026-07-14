import type { PropsWithChildren } from "react";

type DashboardLayoutProps = PropsWithChildren<{
  className?: string;
}>;

export function DashboardLayout({ children, className = "" }: DashboardLayoutProps) {
  return (
    <div className={`relative space-y-5 pb-4 ${className}`}>
      <div className="pointer-events-none absolute inset-x-0 top-0 h-80 overflow-hidden" aria-hidden>
        <div className="absolute -right-16 top-0 h-64 w-64 rounded-full bg-[#8B5CF6]/15 blur-3xl" />
        <div className="absolute left-1/4 top-16 h-48 w-48 rounded-full bg-[#14B8A6]/10 blur-3xl" />
      </div>
      <div className="relative">{children}</div>
    </div>
  );
}
