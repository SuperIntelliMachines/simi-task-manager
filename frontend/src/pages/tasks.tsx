import { useMemo, useState } from "react";

import { Button } from "../components/ui/button";
import { DashboardCard } from "../components/workbench/dashboard-card";
import { useWorkbench } from "../app/providers/workbench-provider";
import { useCompleteTask, useCreateTask, usePatchTask, useSnoozeTask, useTasks } from "../lib/api/hooks";
import { resolveOrgModule, taskDomainForModule } from "../lib/theme/org-module";
import type { TaskDomain, TaskFilters, TaskRecord } from "../lib/api/types";

type TaskFilterFields = Omit<TaskFilters, "organizationId">;

function createDefaultFilterFields(moduleDomain: string): TaskFilterFields {
  return {
    status: "",
    domain: moduleDomain,
    assignee: "",
    dueDate: "",
    priority: "",
  };
}

function taskPriorityTone(priority: TaskRecord["priority"]) {
  if (priority === "high") return "bg-rose-100 text-rose-700";
  if (priority === "medium") return "bg-amber-100 text-amber-700";
  return "bg-emerald-100 text-emerald-700";
}

export function TasksPage() {
  const { organizationId, tenantKey, role } = useWorkbench();
  const moduleDomain = taskDomainForModule(resolveOrgModule(tenantKey));
  const [filterFields, setFilterFields] = useState<TaskFilterFields>(() => createDefaultFilterFields(moduleDomain));
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [draftTitle, setDraftTitle] = useState("");

  const filters = useMemo<TaskFilters | null>(
    () =>
      organizationId != null && organizationId > 0
        ? { ...filterFields, organizationId, domain: moduleDomain }
        : null,
    [filterFields, organizationId, moduleDomain]
  );

  const tasksQuery = useTasks(filters);
  const createTask = useCreateTask(filters);
  const patchTask = usePatchTask(filters);
  const completeTask = useCompleteTask(filters);
  const snoozeTask = useSnoozeTask(filters);

  const selectedTask = useMemo(
    () => tasksQuery.data?.find((task) => task.id === selectedTaskId) ?? null,
    [selectedTaskId, tasksQuery.data]
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-sky-700">Task Workbench</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">Execution surface for managers and staff</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            Filter tasks across domains, inspect detail, and execute manager actions without leaving the workbench.
          </p>
        </div>
        {/* Active query display removed per UX request */}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.8fr_1fr]">
        <div className="space-y-6">
          <DashboardCard title="Filters">
            <div className="grid gap-3 md:grid-cols-3">
              <label className="space-y-2 text-sm text-slate-700">
                <span>Status</span>
                <select
                  aria-label="Status filter"
                  className="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2"
                  value={filterFields.status}
                  onChange={(event) => setFilterFields((current) => ({ ...current, status: event.target.value }))}
                >
                  <option value="">All</option>
                  <option value="open">Open</option>
                  <option value="snoozed">Snoozed</option>
                  <option value="completed">Completed</option>
                  <option value="canceled">Canceled</option>
                </select>
              </label>
              {/* Domain filter removed per request */}
              <label className="space-y-2 text-sm text-slate-700">
                <span>Assignee</span>
                <input
                  aria-label="Assignee filter"
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 font-medium placeholder-slate-500"
                  placeholder="Name"
                  value={filterFields.assignee}
                  onChange={(event) => {
                    const v = event.target.value;
                    setFilterFields((current) => ({ ...current, assignee: v }));
                    try {
                      localStorage.setItem("atm:currentAssigneeFilter", v);
                    } catch {
                      /* ignore */
                    }
                  }}
                />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span>Due Date</span>
                <input
                  aria-label="Due date filter"
                  type="datetime-local"
                  className="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2"
                  value={filterFields.dueDate}
                  onChange={(event) => setFilterFields((current) => ({ ...current, dueDate: event.target.value }))}
                />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span>Priority</span>
                <select
                  aria-label="Priority filter"
                  className="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2"
                  value={filterFields.priority}
                  onChange={(event) => setFilterFields((current) => ({ ...current, priority: event.target.value }))}
                >
                  <option value="">All</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </label>
              <div className="space-y-2 text-sm text-slate-700">
                <span>Name Of The Task</span>
                <div className="flex gap-2">
                  <input
                    aria-label="New task title"
                    className="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2"
                    placeholder="Name of the task"
                    value={draftTitle}
                    onChange={(event) => setDraftTitle(event.target.value)}
                  />
                  <Button
                    onClick={() => {
                      if (!draftTitle.trim() || organizationId == null) return;
                      createTask.mutate({
                        organization_id: organizationId,
                        title: draftTitle,
                        domain: moduleDomain as TaskDomain,
                        due_at: filterFields.dueDate ? new Date(filterFields.dueDate).toISOString() : null,
                        priority: (filterFields.priority || "medium") as "low" | "medium" | "high",
                        actor_user_id: role === "viewer" ? null : 7,
                      });
                      setDraftTitle("");
                    }}
                  >
                    Create
                  </Button>
                </div>
              </div>
            </div>
          </DashboardCard>

          <DashboardCard title="Task List" eyebrow="Operations">
            {tasksQuery.isLoading ? <p className="text-sm text-slate-500">Loading tasks...</p> : null}
            <div className="overflow-hidden rounded-2xl border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 bg-white text-left text-sm">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Task</th>
                    <th className="px-4 py-3 font-medium">Domain</th>
                    <th className="px-4 py-3 font-medium">Assignee</th>
                    <th className="px-4 py-3 font-medium">Due</th>
                    <th className="px-4 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(tasksQuery.data ?? []).map((task) => (
                    <tr key={task.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <button className="text-left" onClick={() => setSelectedTaskId(task.id)}>
                          <div className="font-medium text-slate-900">{task.title}</div>
                          <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                            <span className={`rounded-full px-2 py-1 font-semibold ${taskPriorityTone(task.priority)}`}>{task.priority}</span>
                            <span className="rounded-full bg-slate-100 px-2 py-1 capitalize">{(() => {
                              if (task.status === "open") return "In Progress";
                              if (task.status === "snoozed") return "Snoozed";
                              if (task.status === "completed") return "Completed";
                              if (task.status === "canceled") return "Canceled";
                              return task.status;
                            })()}</span>
                          </div>
                        </button>
                      </td>
                      <td className="px-4 py-3 capitalize text-slate-600">{task.domain.replace("_", " ")}</td>
                      <td className="px-4 py-3 text-slate-600">{task.assignee ?? "Unassigned"}</td>
                      <td className="px-4 py-3 text-slate-600">{task.due_at ? new Date(task.due_at).toLocaleString() : "No due date"}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          <select
                            aria-label="Task actions"
                            defaultValue=""
                            className="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm"
                            onChange={(e) => {
                              const val = e.target.value;
                              if (!val) return;
                              try {
                                if (val === "completed") {
                                  completeTask.mutate({ taskId: task.id, actorUserId: 7 });
                                } else if (val === "in_progress") {
                                  patchTask.mutate({ taskId: task.id, payload: { status: "open", actor_user_id: role === "viewer" ? null : 7 } });
                                } else if (val === "snooze") {
                                  snoozeTask.mutate({ taskId: task.id, dueAt: new Date(Date.now() + 86400000).toISOString(), actorUserId: 7 });
                                } else if (val === "cancel") {
                                  patchTask.mutate({ taskId: task.id, payload: { status: "canceled" } });
                                }
                              } catch {}
                              // reset select
                              (e.target as HTMLSelectElement).value = "";
                            }}
                          >
                            <option value="">Actions</option>
                            <option value="completed">Completed</option>
                            <option value="in_progress">In Progress</option>
                            <option value="snooze">Snooze</option>
                            <option value="cancel">Cancel</option>
                          </select>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </DashboardCard>
        </div>

        <DashboardCard title="Task Detail Drawer" eyebrow="Inspector">
          {selectedTask ? (
            <div className="space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Selected Task</p>
                <h3 className="mt-1 text-2xl font-semibold text-slate-900">{selectedTask.title}</h3>
                <p className="mt-2 text-sm text-slate-600">{selectedTask.description ?? "No description provided."}</p>
              </div>

              <div className="grid gap-3 rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                <div>
                  <p className="font-medium text-slate-900">Assignment Controls</p>
                  <p className="mt-1">Assignee: {selectedTask.assignee ?? "Unassigned"}</p>
                  <p className="text-xs text-slate-500">UI placeholder until assignment mutation lands in the backend API.</p>
                </div>
                <div>
                  <p className="font-medium text-slate-900">Audit Timeline</p>
                  <ol className="mt-2 space-y-2">
                    {selectedTask.audit.map((entry) => (
                      <li key={entry.id} className="rounded-2xl border border-slate-200 bg-white px-3 py-2">
                        <div className="font-medium text-slate-900">{entry.label}</div>
                        <div className="text-xs text-slate-500">{new Date(entry.at).toLocaleString()}</div>
                        {entry.detail ? <div className="mt-1 text-sm text-slate-600">{entry.detail}</div> : null}
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Select a task to inspect details, assignment controls, and the audit trail.</p>
          )}
        </DashboardCard>
      </div>
    </div>
  );
}
