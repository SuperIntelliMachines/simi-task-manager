import React from "react";
import { useWorkbench } from "../app/providers/workbench-provider";

export function DashboardPage() {
  const { tenantLabel } = useWorkbench();
  const t = tenantLabel || localStorage.getItem("atm:tenant") || "Your Organization";
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">Welcome to {t} dashboard</h1>
      <p className="mt-3 text-slate-600">This is a simple placeholder dashboard for the selected organization.</p>
    </div>
  );
}

export default DashboardPage;
