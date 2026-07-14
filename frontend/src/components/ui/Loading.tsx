import React from "react";

export function Loading({ label = "Loading..." }: { label?: string }) {
  return <div className="py-6 text-sm text-slate-600 dark:text-slate-400">{label}</div>;
}

export default Loading;
