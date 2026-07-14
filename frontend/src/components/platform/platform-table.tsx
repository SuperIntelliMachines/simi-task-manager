import type { ReactNode } from "react";

type PlatformTableProps = {
  columns: Array<{ key: string; label: string; className?: string }>;
  rows: Array<{ id: string | number; cells: ReactNode[] }>;
  emptyMessage?: string;
};

export function PlatformTable({ columns, rows, emptyMessage = "No records found." }: PlatformTableProps) {
  if (rows.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200/80 bg-white/50 px-6 py-12 text-center text-sm text-slate-500 dark:border-white/10 dark:bg-slate-950/40 dark:text-slate-400">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white/55 backdrop-blur-xl dark:border-white/10 dark:bg-slate-950/70">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200/80 bg-slate-50/80 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-400">
            <tr>
              {columns.map((column) => (
                <th key={column.key} className={`px-4 py-3 ${column.className ?? ""}`}>
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200/70 dark:divide-white/10">
            {rows.map((row) => (
              <tr key={row.id} className="transition-colors hover:bg-slate-50/80 dark:hover:bg-white/5">
                {row.cells.map((cell, index) => (
                  <td key={`${row.id}-${index}`} className="px-4 py-3 align-middle text-slate-700 dark:text-slate-200">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
