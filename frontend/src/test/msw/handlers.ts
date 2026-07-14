import { delay, http, HttpResponse } from "msw";
import { buildRenewalIntelligenceChart } from "../../lib/utils/renewal-intelligence";

const now = new Date();
const iso = (days: number) => new Date(now.getTime() + days * 24 * 60 * 60 * 1000).toISOString();

const sampleDashboardPolicies = [
  { id: 11, policy_number: "POL-2026-441", policyholder_name: "Ravi Sharma", policy_type: "Auto", renewal_frequency: "yearly", expiry_date: iso(5), premium: 18500, status: "active", assigned_agent_user_id: "Kumar" },
  { id: 103, policy_number: "POL-2026-443", policyholder_name: "Ramesh Gupta", policy_type: "Life", renewal_frequency: "monthly", expiry_date: iso(2), premium: 32000, status: "active", assigned_agent_user_id: "Anika" },
  { id: 12, policy_number: "POL-2026-118", policyholder_name: "Asha Patel", policy_type: "Health", renewal_frequency: "quarterly", expiry_date: iso(-1), premium: 15600, status: "active", assigned_agent_user_id: "Leo" },
  { id: 107, policy_number: "POL-2026-447", policyholder_name: "Vikram Singh", policy_type: "Auto", renewal_frequency: "yearly", expiry_date: iso(18), premium: 19800, status: "renewed", assigned_agent_user_id: "Kumar" },
];

const sampleRenewalIntelligence = buildRenewalIntelligenceChart(sampleDashboardPolicies);

type Task = {
  id: number;
  organization_id: number;
  title: string;
  description: string | null;
  domain: string;
  status: string;
  due_at: string | null;
  priority: string;
  assignee: string | null;
  audit: Array<{ id: string; label: string; at: string; detail?: string }>;
};

const seedTasks = (): Task[] => [
  {
    id: 1,
    organization_id: 1,
    title: "Renew Ravi policy bundle",
    description: "Coordinate renewal copy and WhatsApp reminder.",
    domain: "insurance",
    status: "open",
    due_at: iso(2),
    priority: "high",
    assignee: "Maya",
    audit: [{ id: "a-1", label: "Task created", at: iso(-1), detail: "Created by manager" }],
  },
  {
    id: 2,
    organization_id: 1,
    title: "Tomorrow prep checklist",
    description: "Internal preparation runbook.",
    domain: "medical_office",
    status: "open",
    due_at: iso(1),
    priority: "medium",
    assignee: "Anika",
    audit: [{ id: "a-2", label: "Assigned", at: iso(-2) }],
  },
  {
    id: 3,
    organization_id: 2,
    title: "General onboarding checklist",
    description: "Welcome new team members.",
    domain: "general",
    status: "open",
    due_at: iso(3),
    priority: "medium",
    assignee: "Alex",
    audit: [{ id: "a-3", label: "Task created", at: iso(-1) }],
  },
  {
    id: 4,
    organization_id: 2,
    title: "Lead follow-up",
    description: "Should never appear for org 2 when domain filter is general.",
    domain: "insurance",
    status: "open",
    due_at: iso(1),
    priority: "high",
    assignee: "Maya",
    audit: [{ id: "a-4", label: "Task created", at: iso(-1) }],
  },
];

let tasks = seedTasks();
let lastTasksUrl: URL | null = null;
let lastCompletedTaskId: number | null = null;
let insuranceMode: "populated" | "empty" | "loading" = "populated";
let mockAuthOrgId = 2;

export function resetMswState() {
  tasks = seedTasks();
  lastTasksUrl = null;
  lastCompletedTaskId = null;
  insuranceMode = "populated";
  mockAuthOrgId = 2;
}

export function setMockAuthOrg(orgId: number) {
  mockAuthOrgId = orgId;
}

export function getLastTasksUrl() {
  return lastTasksUrl;
}

export function getLastCompletedTaskId() {
  return lastCompletedTaskId;
}

export function setInsuranceDashboardMode(mode: "populated" | "empty" | "loading") {
  insuranceMode = mode;
}

function filterTasks(url: URL) {
  const organizationId = url.searchParams.get("organization_id");
  return tasks.filter((task) => {
    if (organizationId && task.organization_id !== Number(organizationId)) return false;
    const status = url.searchParams.get("status");
    const domain = url.searchParams.get("domain");
    const assignee = url.searchParams.get("assignee");
    const dueDate = url.searchParams.get("due_date");
    const priority = url.searchParams.get("priority");
    if (status && task.status !== status) return false;
    if (domain && task.domain !== domain) return false;
    if (assignee && task.assignee !== assignee) return false;
    if (dueDate && (!task.due_at || task.due_at.slice(0, 10) !== dueDate)) return false;
    if (priority && task.priority !== priority) return false;
    return true;
  });
}

export const handlers = [
  http.get("/healthz", () => HttpResponse.json({ status: "ok" })),
  http.get("/api/v1/auth/me", () =>
    HttpResponse.json({
      id: 1,
      email: "test@example.com",
      role: "manager",
      organization_id: mockAuthOrgId,
      organization_name: mockAuthOrgId === 2 ? "General" : "Insurance",
    })
  ),
  http.get("/api/v1/tasks", ({ request }) => {
    lastTasksUrl = new URL(request.url);
    return HttpResponse.json(filterTasks(lastTasksUrl));
  }),
  http.post("/api/v1/tasks", async ({ request }) => {
    const body = (await request.json()) as { organization_id: number; title: string; domain: string; due_at?: string | null };
    const task: Task = {
      id: tasks.length + 1,
      organization_id: body.organization_id,
      title: body.title,
      description: null,
      domain: body.domain,
      status: "open",
      due_at: body.due_at ?? null,
      priority: "medium",
      assignee: null,
      audit: [{ id: `task-${tasks.length + 1}`, label: "Task created", at: new Date().toISOString() }],
    };
    tasks = [task, ...tasks];
    return HttpResponse.json(task);
  }),
  http.patch("/api/v1/tasks/:taskId", async ({ params, request }) => {
    const taskId = Number(params.taskId);
    const body = (await request.json()) as Partial<Task>;
    tasks = tasks.map((task) => (task.id === taskId ? { ...task, ...body } : task));
    return HttpResponse.json(tasks.find((task) => task.id === taskId));
  }),
  http.post("/api/v1/tasks/:taskId/complete", ({ params }) => {
    const taskId = Number(params.taskId);
    lastCompletedTaskId = taskId;
    tasks = tasks.map((task) => (task.id === taskId ? { ...task, status: "completed" } : task));
    return HttpResponse.json(tasks.find((task) => task.id === taskId));
  }),
  http.post("/api/v1/tasks/:taskId/snooze", async ({ params, request }) => {
    const taskId = Number(params.taskId);
    const body = (await request.json()) as { due_at: string };
    tasks = tasks.map((task) => (task.id === taskId ? { ...task, status: "snoozed", due_at: body.due_at } : task));
    return HttpResponse.json(tasks.find((task) => task.id === taskId));
  }),
  http.get("/api/v1/approval-requests", () =>
    HttpResponse.json([
      {
        id: 501,
        organization_id: 1,
        status: "pending",
        reason: "Bulk renewal reminders require approval.",
        proposed_action: { action_type: "create_premium_reminder", payload: { audience: "expiring_customers" } },
        created_at: iso(-1),
      },
    ])
  ),
  http.get("/api/v1/channel-connections", () =>
    HttpResponse.json([
      {
        id: 1,
        organization_id: 1,
        channel: "telegram",
        status: "active",
        provider_reference: "tg-workspace-01",
        settings: { botToken: "telegram-token", testRecipient: "@ops_team" },
      },
      {
        id: 2,
        organization_id: 1,
        channel: "whatsapp",
        status: "draft",
        provider_reference: "",
        settings: { phoneNumberId: "", testRecipient: "+15550001" },
      },
    ])
  ),
  http.post("/api/v1/channel-connections", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 3, ...body });
  }),
  http.post("/api/v1/channel-connections/:connectionId/test", async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: Number(params.connectionId) * 10, status: "sent", ...body });
  }),
  http.get("/api/v1/notification-preferences", () =>
    HttpResponse.json([
      {
        id: 21,
        organization_id: 1,
        contact_id: 41,
        user_id: null,
        purpose: "reminder",
        preferred_channel: ["whatsapp"],
        fallback_channel: "telegram",
        opt_out: false,
      },
    ])
  ),
  http.put("/api/v1/notification-preferences/:preferenceId", async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: Number(params.preferenceId), organization_id: 1, contact_id: 41, user_id: null, purpose: "reminder", fallback_channel: "telegram", opt_out: false, ...body });
  }),
  http.get("/api/v1/insurance/policies", async () => {
    if (insuranceMode === "loading") {
      await delay(200);
    }
    if (insuranceMode === "empty") {
      return HttpResponse.json([]);
    }
    return HttpResponse.json([
      { id: 11, policy_number: "POL-2026-441", policyholder_name: "Ravi Sharma", policy_type: "Auto", expiry_date: iso(5), preferred_channel: ["whatsapp"], status: "active" },
      { id: 103, policy_number: "POL-2026-443", policyholder_name: "Ramesh Gupta", policy_type: "Life", expiry_date: iso(2), preferred_channel: ["whatsapp"], status: "active" },
      { id: 12, policy_number: "POL-2026-118", policyholder_name: "Asha Patel", policy_type: "Health", expiry_date: iso(-1), preferred_channel: ["telegram"], status: "active" },
    ]);
  }),
  http.get("/api/v1/insurance/followups", async () => {
    if (insuranceMode === "empty") {
      return HttpResponse.json([]);
    }
    return HttpResponse.json([
      { id: 88, customerName: "Priya Nair", contact_name: "Priya Nair", status: "follow_up_pending", followup_due_at: iso(3) },
    ]);
  }),
  http.get("/api/v1/insurance/dashboard", async () => {
    if (insuranceMode === "loading") {
      await delay(200);
    }
    if (insuranceMode === "empty") {
      return HttpResponse.json({
        due_renewals: [],
        expiring_policies: [],
        grace_period_policies: [],
        lapsed_policies: [],
        pending_followups: [],
        counts: {
          active_policies: 0,
          expiring_policies: 0,
          due_renewals: 0,
          grace_period_policies: 0,
          lapsed_policies: 0,
          pending_followups: 0,
          due_followups: 0,
          overdue_followups: 0,
        },
        policy_summary: {
          total_policies: 0,
          active_policies: 0,
          grace_period_policies: 0,
          lapsed_policies: 0,
          expiring_soon_policies: 0,
        },
        lead_followup_overview: {
          total_leads: 0,
          upcoming_followups: 0,
          due_in_48_hours: 0,
          missed_followups: 0,
        },
        renewal_intelligence: { points: [], filters: { agents: [], product_types: [] } },
        conversion_metrics: { demo_to_policy_rate: 0, renewal_rate: 0 },
      });
    }
    return HttpResponse.json({
      due_renewals: [
        { id: 11, policy_number: "POL-2026-441", policyholder_name: "Ravi Sharma", policy_type: "Auto", expiry_date: iso(5), preferred_channel: ["whatsapp"], status: "active" },
      ],
      expiring_policies: [
        { id: 103, policy_number: "POL-2026-443", policyholder_name: "Ramesh Gupta", policy_type: "Life", expiry_date: iso(2), preferred_channel: ["whatsapp"], status: "active" },
      ],
      grace_period_policies: [
        { id: 12, policy_number: "POL-2026-118", policyholder_name: "Asha Patel", policy_type: "Health", expiry_date: iso(-1), preferred_channel: ["telegram"], status: "active" },
      ],
      lapsed_policies: [],
      pending_followups: [
        { id: 88, customerName: "Priya Nair", contact_name: "Priya Nair", status: "follow_up_pending", followup_due_at: iso(3) },
      ],
      counts: {
        active_policies: 5,
        expiring_policies: 1,
        due_renewals: 1,
        grace_period_policies: 1,
        lapsed_policies: 0,
        pending_followups: 1,
        due_followups: 1,
        overdue_followups: 1,
      },
      policy_summary: {
        total_policies: 3,
        active_policies: 2,
        grace_period_policies: 1,
        lapsed_policies: 0,
        expiring_soon_policies: 2,
      },
      lead_followup_overview: {
        total_leads: 2,
        upcoming_followups: 1,
        due_in_48_hours: 0,
        missed_followups: 1,
      },
      renewal_intelligence: sampleRenewalIntelligence,
      conversion_metrics: { demo_to_policy_rate: 62, renewal_rate: 84 },
    });
  }),
];
