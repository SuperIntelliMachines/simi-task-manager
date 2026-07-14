import React from "react";

export function EmptyState({ title, message }: { title?: string; message: string }) {
  return (
    <div className="rounded-2xl bg-white/70 dark:bg-card backdrop-blur-xl p-6">
      {title ? <p className="text-sm font-semibold text-slate-900 dark:text-white">{title}</p> : null}
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{message}</p>
    </div>
  );
}

export default EmptyState;
