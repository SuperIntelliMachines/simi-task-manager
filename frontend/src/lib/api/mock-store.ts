import type {
  ApprovalRequestRecord,
  ChannelConnectionInput,
  ChannelConnectionRecord,
  CommandPreview,
  ConstructionDashboard,
  InsuranceDashboard,
  MedicalDashboard,
  NotificationPreferenceRecord,
  TaskCreateInput,
  TaskFilters,
  TaskPatchInput,
  TaskRecord,
} from "./types";
import { countFollowupsDueToday, countFollowupsOverdue } from "../utils/followup-due-filter";
import { isActivePolicy } from "../utils/policy-classifier";

const now = new Date();
const iso = (days: number) => new Date(now.getTime() + days * 24 * 60 * 60 * 1000).toISOString();
// Return a UTC date-only string YYYY-MM-DD for predictable, timezone-free comparisons
const isoDateOnly = (days: number) => {
  const d = new Date(now.getTime() + days * 24 * 60 * 60 * 1000);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
};

let nextTaskId = 6;
let nextConnectionId = 3;
// Try to persist mock tasks in localStorage for development convenience
const MOCK_TASKS_KEY = "atm:mockTasks";

let mockTasks: TaskRecord[] = [];

function loadMockTasks() {
  try {
    const raw = localStorage.getItem(MOCK_TASKS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as TaskRecord[];
      if (Array.isArray(parsed)) {
        return parsed;
      }
    }
  } catch {
    // ignore
  }
  return null;
}

function saveMockTasks() {
  try {
    localStorage.setItem(MOCK_TASKS_KEY, JSON.stringify(mockTasks));
  } catch {
    // ignore
  }
}

// default seed tasks
let seededTasks: TaskRecord[] = [
  {
    id: 1,
    organization_id: 1,
    title: "Renew Ravi policy bundle",
    description: "Coordinate renewal copy and WhatsApp reminder.",
    domain: "insurance",
    status: "open",
    due_at: iso(2),
    priority: "high",
    assignee: "Name",
    audit: [
      { id: "1-a", label: "Task created", at: iso(-2), detail: "Created by manager" },
      { id: "1-b", label: "Reminder draft approved", at: iso(-1), detail: "Bulk approval granted" },
    ],
  },
  {
    id: 2,
    organization_id: 1,
    title: "Site A wiring progress update",
    description: "Collect completion percentage from Kumar.",
    domain: "construction",
    status: "snoozed",
    due_at: iso(1),
    priority: "medium",
    assignee: "Kumar",
    audit: [{ id: "2-a", label: "Task snoozed", at: iso(-1), detail: "Deferred until crew sync" }],
  },
  {
    id: 3,
    organization_id: 1,
    title: "Tomorrow prep checklist",
    description: "Redacted prep for clinic schedule.",
    domain: "medical_office",
    status: "open",
    due_at: iso(0),
    priority: "high",
    assignee: "Anika",
    audit: [{ id: "3-a", label: "Task assigned", at: iso(-3), detail: "Assigned to front desk" }],
  },
  {
    id: 4,
    organization_id: 2,
    title: "General onboarding checklist",
    description: "Welcome new team members.",
    domain: "general",
    status: "open",
    due_at: iso(3),
    priority: "medium",
    assignee: "Alex",
    audit: [{ id: "4-a", label: "Task created", at: iso(-1) }],
  },
  {
    id: 5,
    organization_id: 2,
    title: "Policy renewal",
    description: "Insurance task in org 2 for isolation tests.",
    domain: "insurance",
    status: "open",
    due_at: iso(2),
    priority: "high",
    assignee: "Maya",
    audit: [{ id: "5-a", label: "Task created", at: iso(-1) }],
  },
];

const loaded = loadMockTasks();
if (loaded) {
  mockTasks = loaded;
  nextTaskId = (mockTasks.reduce((m, t) => Math.max(m, t.id), 0) || 0) + 1;
} else {
  mockTasks = seededTasks;
  nextTaskId = (mockTasks.reduce((m, t) => Math.max(m, t.id), 0) || 0) + 1;
  saveMockTasks();
}

let mockApprovals: ApprovalRequestRecord[] = [
  {
    id: 501,
    organization_id: 1,
    status: "pending",
    reason: "Bulk renewal reminders require approval.",
    proposed_action: { action_type: "create_premium_reminder", payload: { audience: "expiring_customers" } },
    created_at: iso(-1),
  },
];

let mockConnections: ChannelConnectionRecord[] = [
  {
    id: 1,
    organization_id: 1,
    channel: "telegram",
    status: "active",
    provider_reference: "tg-workspace-01",
    settings: { botToken: "configured", testRecipient: "@ops_team" },
  },
  {
    id: 2,
    organization_id: 1,
    channel: "whatsapp",
    status: "draft",
    provider_reference: null,
    settings: { phoneNumberId: "", testRecipient: "+15550001" },
  },
];

let mockPreferences: NotificationPreferenceRecord[] = [
  {
    id: 21,
    organization_id: 1,
    contact_id: 41,
    user_id: null,
    purpose: "reminder",
    preferred_channel: "whatsapp",
    fallback_channel: "telegram",
    opt_out: false,
  },
  {
    id: 22,
    organization_id: 1,
    contact_id: 42,
    user_id: null,
    purpose: "reminder",
    preferred_channel: "telegram",
    fallback_channel: null,
    opt_out: true,
  },
];

const insuranceDashboard: InsuranceDashboard = {
  due_renewals: [
    {
      id: 11,
      policy_number: "POL-2026-441",
      policyholder_name: "Ravi Sharma",
      policy_type: "Auto",
      expiry_date: iso(5),
      preferred_channel: ["whatsapp"],
      status: "active",
    },
  ],
  expiring_policies: [],
  grace_period_policies: [
    {
      id: 12,
      policy_number: "POL-2026-118",
      policyholder_name: "Asha Patel",
      policy_type: "Health",
      expiry_date: iso(-1),
      preferred_channel: ["telegram"],
      status: "active",
    },
  ],
  pending_followups: [
    {
      id: 88,
      contact_name: "Priya Nair",
      status: "follow_up_pending",
      followup_due_at: iso(3),
    },
  ],
  lapsed_policies: [],
  counts: { due_renewals: 1, grace_period_policies: 1, lapsed_policies: 0, pending_followups: 1, due_followups: 0, overdue_followups: 0 },
  conversion_metrics: { demo_to_policy_rate: 62, renewal_rate: 84 },
};

// Mock policies for insurance module
let nextPolicyId = 200;
const mockPolicies: any[] = [
  // examples relative to `now` (use iso offsets defined above)
  { id: 101, organization_id: 1, policy_number: "POL-2026-441", policyholder_name: "Ravi Sharma", policy_type: "Auto", renewal_frequency: "yearly", expiry_date: isoDateOnly(10), carrier: "Acme Insure", premium: 18500, currency: "INR", mobile: "+91 98765 43210", status: "active", assigned_agent_user_id: "Kumar" },
  { id: 102, organization_id: 1, policy_number: "POL-2026-442", policyholder_name: "Sunita Rao", policy_type: "Health", renewal_frequency: "quarterly", expiry_date: isoDateOnly(5), carrier: "GoodHealth", premium: 24000, currency: "INR", mobile: "+91 91234 56789", status: "active", assigned_agent_user_id: "Anika" },
  { id: 103, organization_id: 1, policy_number: "POL-2026-443", policyholder_name: "Ramesh Gupta", policy_type: "Life", renewal_frequency: "monthly", expiry_date: isoDateOnly(2), carrier: "LifeSafe", premium: 32000, currency: "INR", mobile: "+91 99887 76655", status: "active", assigned_agent_user_id: "Kumar" },
  { id: 104, organization_id: 1, policy_number: "POL-2026-444", policyholder_name: "Meera Joshi", policy_type: "Health", renewal_frequency: "half_yearly", expiry_date: isoDateOnly(1), carrier: "GoodHealth", premium: 15600, currency: "INR", mobile: "+91 97654 32109", status: "active", assigned_agent_user_id: null },
  { id: 105, organization_id: 1, policy_number: "POL-2026-445", policyholder_name: "Arun Patel", policy_type: "Auto", renewal_frequency: "yearly", expiry_date: isoDateOnly(0), carrier: "Acme Insure", premium: 21000, currency: "INR", mobile: "+91 90123 45678", status: "active", assigned_agent_user_id: "Fatima" },
  { id: 106, organization_id: 1, policy_number: "POL-2026-446", policyholder_name: "Asha Patel", policy_type: "Health", renewal_frequency: "yearly", expiry_date: isoDateOnly(-1), carrier: "GoodHealth", status: "active", assigned_agent_user_id: "Leo" },
  { id: 107, organization_id: 1, policy_number: "POL-2026-447", policyholder_name: "Vikram Singh", policy_type: "Auto", renewal_frequency: "yearly", expiry_date: isoDateOnly(18), carrier: "Acme Insure", premium: 19800, currency: "INR", mobile: "+91 93456 78901", status: "active", assigned_agent_user_id: "Kumar" },
];

function parseDateOnlyToUTC(dateStr: string) {
  if (!dateStr) return null;
  // Accept DD-MM-YYYY
  const ddmm = /^\s*(\d{2})-(\d{2})-(\d{4})\s*$/.exec(dateStr);
  if (ddmm) {
    const day = Number(ddmm[1]);
    const month = Number(ddmm[2]) - 1;
    const year = Number(ddmm[3]);
    return new Date(Date.UTC(year, month, day));
  }
  // Accept YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss
  const ymd = /^\s*(\d{4})-(\d{2})-(\d{2})/.exec(dateStr);
  if (ymd) {
    const year = Number(ymd[1]);
    const month = Number(ymd[2]) - 1;
    const day = Number(ymd[3]);
    return new Date(Date.UTC(year, month, day));
  }
  // Fallback: try Date parser, then normalize to UTC date-only
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
}

const mockPolicyReminders = new Map<number, any[]>();
let nextPolicyReminderId = 5000;

function buildMockPolicyReminders(policyId: number, expiryDate: string) {
  const expiry = parseDateOnlyToUTC(expiryDate);
  if (!expiry) return [];
  const offsets = [
    ["DUE_30_DAYS", -30, 30],
    ["DUE_15_DAYS", -15, 15],
    ["UPCOMING_10_DAYS", -10, 10],
    ["UPCOMING_5_DAYS", -5, 5],
    ["CRITICAL_2_DAYS", -2, 2],
    ["CRITICAL_1_DAY", -1, 1],
    ["EXPIRY_DAY", 0, 0],
    ["ESCALATION", 1, -1],
  ] as const;
  return offsets.map(([reminder_type, dayOffset, stage]) => {
    const reminderAt = new Date(expiry);
    reminderAt.setUTCDate(reminderAt.getUTCDate() + dayOffset);
    return {
      id: nextPolicyReminderId++,
      policy_id: policyId,
      reminder_type,
      reminder_at: reminderAt.toISOString(),
      stage,
      status: "PENDING",
      channel: "whatsapp",
      sent_at: null,
    };
  });
}

function daysUntil(dateIso: string) {
  try {
    const targetDate = parseDateOnlyToUTC(dateIso);
    if (!targetDate) return NaN;
    const now = new Date();
    const utcStart = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
    const utcTarget = Date.UTC(targetDate.getUTCFullYear(), targetDate.getUTCMonth(), targetDate.getUTCDate());
    const diff = (utcTarget - utcStart) / (1000 * 60 * 60 * 24);
    return Math.round(diff);
  } catch {
    return NaN;
  }
}

function classifyPolicies() {
  const dueRenewals: any[] = [];
  const expiring: any[] = [];
  const gracePeriod: any[] = [];
  const lapsed: any[] = [];

  mockPolicies.forEach((p) => {
    const days = daysUntil(p.expiry_date);
    if (Number.isNaN(days)) return;
    let category = "unknown";
    if (days < 0) {
      if (Math.abs(days) <= 30) {
        gracePeriod.push(p);
        category = "grace_period";
      } else {
        lapsed.push(p);
        category = "lapsed";
      }
    } else if (days <= 2) {
      // 0,1,2 days => Expiring Policies
      expiring.push(p);
      category = "expiring";
    } else if (days >= 3 && days <= 10) {
      // 3..10 days => Due Renewals
      dueRenewals.push(p);
      category = "due";
    }
    // Log full details for debugging: policy number, holder, expiry, UTC today, days remaining, category
    console.log && console.log("[PolicyClassify]", {
      policy_number: p.policy_number,
      policyholder_name: p.policyholder_name,
      expiry: p.expiry_date,
      utc_today: new Date().toUTCString(),
      daysRemaining: days,
      category,
    });
  });

  return { dueRenewals, expiring, gracePeriod, lapsed };
}

// simple in-memory leads/followups for mocking
let nextLeadId = 100;
const mockLeads: any[] = [
  {
    id: 88,
    organization_id: 1,
    contact_name: "Priya Nair",
    status: "follow_up_pending",
    followup_due_at: iso(3),
    notes: "Interested in health policy",
    assigned_agent_user_id: null,
    source: "demo",
  },
  {
    id: 89,
    organization_id: 1,
    contact_name: "Test Pending",
    status: "open",
    customer_decision: "Pending",
    followup_due_at: iso(5), // due 2026-06-09 in current mock timeline
    notes: "Added for pending-count verification",
    assigned_agent_user_id: null,
    source: "demo",
  },
  {
    id: 90,
    organization_id: 1,
    contact_name: "Due Today Lead",
    status: "follow_up_pending",
    followup_due_at: iso(0),
    notes: "Follow-up due today",
    assigned_agent_user_id: null,
    source: "demo",
  },
  {
    id: 91,
    organization_id: 1,
    contact_name: "Overdue Lead",
    status: "interested",
    followup_due_at: iso(-3),
    notes: "Overdue follow-up",
    assigned_agent_user_id: null,
    source: "demo",
  },
];

function pickMockPolicyForLead(lead: any) {
  const relatedId = lead.related_policy_id;
  if (relatedId != null) {
    const direct = mockPolicies.find((p) => p.id === relatedId);
    if (direct) return direct;
  }
  let candidates = mockPolicies;
  if (lead.contact_id != null) {
    candidates = mockPolicies.filter((p) => p.policyholder_id === lead.contact_id);
  } else if (lead.contact_name) {
    const name = String(lead.contact_name).toLowerCase();
    candidates = mockPolicies.filter((p) => {
      const holder = String(p.policyholder_name || "").toLowerCase();
      return holder === name || holder.startsWith(name) || name.startsWith(holder.split(" ")[0]);
    });
  }
  const active = candidates.filter((p) => (p.status || "").toLowerCase() === "active");
  const pool = active.length > 0 ? active : candidates;
  if (pool.length === 0) return null;
  return pool.sort((a, b) => b.id - a.id)[0];
}

function policyTypeFromNotes(notes: string | null | undefined): string | null {
  if (!notes) return null;
  for (const line of notes.split("\n")) {
    const stripped = line.trim();
    if (stripped.toLowerCase().startsWith("policy type:")) {
      return stripped.split(":").slice(1).join(":").trim() || null;
    }
  }
  return null;
}

function enrichMockFollowup(lead: any) {
  const customerName = lead.customerName ?? lead.contact_name ?? null;
  const policy = pickMockPolicyForLead(lead);
  const contactPhone = lead.contact_phone ?? lead.phone ?? policy?.mobile ?? null;
  const contactEmail = lead.contact_email ?? lead.email ?? null;
  return {
    ...lead,
    customerName,
    contact_name: customerName,
    contact_phone: contactPhone,
    contact_email: contactEmail,
    email: contactEmail,
    phone: contactPhone,
    policyType: policy?.policy_type ?? policyTypeFromNotes(lead.notes) ?? null,
    followUpDate: lead.followUpDate ?? lead.followup_due_at ?? null,
  };
}

function listMockFollowups(organizationId: number, status?: string) {
  let rows = mockLeads.filter((l) => l.organization_id === organizationId);
  if (status) rows = rows.filter((r) => r.status === status);
  return rows.map(enrichMockFollowup);
}

function createMockLead(input: any) {
  const customerName = input.contact_name || input.customerName || "Unnamed Customer";
  const contactPhone = input.contact_phone?.trim() || null;
  const contactEmail = input.contact_email?.trim() || null;
  let notes = input.notes ?? null;
  if (input.insurance_type) {
    const label = String(input.insurance_type).trim().charAt(0).toUpperCase() + String(input.insurance_type).trim().slice(1);
    const prefix = `Policy Type: ${label}`;
    notes = notes ? `${prefix}\n${notes}` : prefix;
  }
  const lead = {
    id: nextLeadId++,
    organization_id: input.organization_id,
    contact_name: customerName,
    customerName,
    contact_phone: contactPhone,
    contact_email: contactEmail,
    phone: contactPhone,
    email: contactEmail,
    status: input.status ?? "open",
    followup_due_at: input.followup_due_at ?? null,
    followUpDate: input.followup_due_at ?? null,
    notes,
    assigned_agent_user_id: input.assigned_agent_user_id ?? null,
    source: input.source ?? null,
    demo_logged_at: input.demo_logged_at ?? null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  mockLeads.unshift(lead);
  return enrichMockFollowup(lead);
}

function patchMockLead(leadId: number, updates: any) {
  const idx = mockLeads.findIndex((l) => l.id === leadId);
  if (idx === -1) throw new Error("lead not found");
  const lead = mockLeads[idx];
  Object.assign(lead, updates);
  lead.updated_at = new Date().toISOString();
  return lead;
}

function startMockLeadWorkflow(leadId: number, body: any) {
  const lead = mockLeads.find((l) => l.id === leadId);
  if (!lead) throw new Error("lead not found");
  const scheduled = body.followup_due_at ?? iso(body.days_until_followup ?? 3);
  lead.status = "follow_up_pending";
  lead.followup_due_at = scheduled;
  lead.updated_at = new Date().toISOString();
  return { lead, reminder: { id: leadId + 1000, scheduled_for: scheduled } };
}

function startMockPolicyWorkflow(policyId: number, body: any) {
  const policy = mockPolicies.find((p) => p.id === policyId);
  if (!policy) throw new Error("policy not found");
  return { policy, workflow: { id: policyId + 2000, ...body } };
}

const constructionDashboard: ConstructionDashboard = {
  overdueTasks: 4,
  blockedTasks: 2,
  workerLoad: [
    { name: "Kumar", openTasks: 6 },
    { name: "Fatima", openTasks: 4 },
    { name: "Leo", openTasks: 3 },
  ],
  siteProgress: [
    { site: "Site A", completion: 72 },
    { site: "Site B", completion: 48 },
  ],
};

const medicalDashboard: MedicalDashboard = {
  tomorrowPrep: [
    { id: "p1", patient: "Elena Morris", summary: "Insurance verification and labs prep" },
    { id: "p2", patient: "David Chen", summary: "Referral packet review" },
  ],
  overdueInternalTasks: 5,
  queues: [
    { id: "q1", patient: "Elena Morris", lane: "referrals", owner: "Front Desk" },
    { id: "q2", patient: "David Chen", lane: "billing", owner: "Billing" },
  ],
};

function filterTasks(filters: TaskFilters) {
  return mockTasks.filter((task) => {
    if (filters.status && task.status !== filters.status) return false;
    if (filters.domain && task.domain !== filters.domain) return false;
    if (filters.assignee && task.assignee !== filters.assignee) return false;
    if (filters.priority && task.priority !== filters.priority) return false;
    if (filters.dueDate) {
      if (!task.due_at) return false;
      const due = task.due_at.slice(0, 10);
      if (due !== filters.dueDate) return false;
    }
    return task.organization_id === filters.organizationId;
  });
}

export const mockApi = {
  listTasks(filters: TaskFilters) {
    return filterTasks(filters);
  },
  createTask(input: TaskCreateInput) {
    const task: TaskRecord = {
      id: nextTaskId++,
      organization_id: input.organization_id,
      title: input.title,
      description: input.description ?? null,
      domain: input.domain,
      status: "open",
      due_at: input.due_at ?? null,
        priority: (input as any).priority ?? "medium",
      assignee: (function () {
        try {
          const f = localStorage.getItem("atm:currentAssigneeFilter");
          if (f && f.trim() !== "") return f;
          return localStorage.getItem("atm:currentUserName") ?? null;
        } catch {
          return null;
        }
      })(),
      audit: [{ id: `${Date.now()}-created`, label: "Task created", at: new Date().toISOString() }],
    };
    mockTasks = [task, ...mockTasks];
    saveMockTasks();
    return task;
  },
  patchTask(id: number, input: TaskPatchInput) {
    mockTasks = mockTasks.map((task) =>
      task.id === id
        ? {
            ...task,
            ...input,
            audit: [
              { id: `${Date.now()}-updated`, label: "Task updated", at: new Date().toISOString() },
              ...task.audit,
            ],
          }
        : task
    );
    return mockTasks.find((task) => task.id === id)!;
  },
  completeTask(id: number) {
    return this.patchTask(id, { status: "completed" });
  },
  snoozeTask(id: number, dueAt: string) {
    return this.patchTask(id, { status: "snoozed", due_at: dueAt });
  },
  listApprovals() {
    return mockApprovals;
  },
  listConnections() {
    return mockConnections;
  },
  upsertConnection(input: ChannelConnectionInput) {
    const existing = mockConnections.find((item) => item.channel === input.channel);
    if (existing) {
      Object.assign(existing, {
        provider_reference: input.provider_reference,
        status: input.status ?? existing.status,
        settings: input.settings,
      });
      return existing;
    }
    const row: ChannelConnectionRecord = {
      id: nextConnectionId++,
      organization_id: input.organization_id,
      channel: input.channel,
      status: input.status ?? "active",
      provider_reference: input.provider_reference,
      settings: input.settings,
    };
    mockConnections = [...mockConnections, row];
    return row;
  },
  sendTestMessage(connectionId: number, body: { recipient: string; text: string }) {
    return { id: connectionId * 100, status: "sent", channel: mockConnections.find((item) => item.id === connectionId)?.channel ?? "telegram", recipient: body.recipient, body: body.text };
  },
  listPreferences() {
    return mockPreferences;
  },
  updatePreference(id: number, updates: Partial<NotificationPreferenceRecord>) {
    mockPreferences = mockPreferences.map((item) => (item.id === id ? { ...item, ...updates } : item));
    return mockPreferences.find((item) => item.id === id)!;
  },
  insuranceDashboard(empty = false) {
    if (empty) {
      return {
        ...insuranceDashboard,
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
      } satisfies InsuranceDashboard;
    }

    const { dueRenewals, expiring, gracePeriod, lapsed } = classifyPolicies();
    const openWithDue = mockLeads.filter((l) => l.followup_due_at);
    return {
      due_renewals: dueRenewals,
      expiring_policies: expiring,
      grace_period_policies: gracePeriod,
      lapsed_policies: lapsed,
      pending_followups: openWithDue.slice(0, 10),
      counts: {
        active_policies: mockPolicies.filter(isActivePolicy).length,
        expiring_policies: expiring.length,
        due_renewals: dueRenewals.length,
        grace_period_policies: gracePeriod.length,
        lapsed_policies: lapsed.length,
        pending_followups: openWithDue.length,
        due_followups: countFollowupsDueToday(mockLeads),
        overdue_followups: countFollowupsOverdue(mockLeads),
      },
      conversion_metrics: insuranceDashboard.conversion_metrics,
    } as unknown as InsuranceDashboard;
  },
  // followups / leads
  listFollowups(organizationId: number, status?: string) {
    return listMockFollowups(organizationId, status);
  },
  listPolicies(organizationId: number, status?: string) {
    // If a status filter is provided, return the matching bucket according to business rules.
    const { dueRenewals, expiring, gracePeriod, lapsed } = classifyPolicies();
    // In mock mode, ignore organizationId filtering to make development simpler
    const all = mockPolicies; // mockPolicies.filter((p) => p.organization_id === organizationId);
    console.log && console.log("[mockApi.listPolicies] returning policies", { organizationId, status, total: all.length });
    all.forEach((p) => {
      const days = daysUntil(p.expiry_date);
      console.log && console.log("[mockApi.listPolicies.policy]", { policy_number: p.policy_number, policyholder_name: p.policyholder_name, expiry: p.expiry_date, daysRemaining: days });
    });

    if (!status) return all;
    if (status === "due") return dueRenewals.filter((p) => p.organization_id === organizationId);
    if (status === "expiring") return expiring.filter((p) => p.organization_id === organizationId);
    if (status === "grace_period") return gracePeriod.filter((p) => p.organization_id === organizationId);
    if (status === "lapsed") return lapsed.filter((p) => p.organization_id === organizationId);
    if (status === "active") {
      return mockPolicies.filter(
        (p) => p.organization_id === organizationId && isActivePolicy(p),
      );
    }
    // unknown status: return all for now
    return all;
  },
  getPolicy(policyId: number) {
    const policy = mockPolicies.find((item) => item.id === policyId);
    if (!policy) {
      throw new Error("Policy not found");
    }
    return { ...policy };
  },
  updatePolicy(policyId: number, updates: Record<string, unknown>) {
    const index = mockPolicies.findIndex((item) => item.id === policyId);
    if (index === -1) {
      throw new Error("Policy not found");
    }

    const current = mockPolicies[index];
    const next: Record<string, unknown> = { ...current, ...updates };

    if (typeof next.expiry_date === "string" && next.expiry_date.includes("T")) {
      next.expiry_date = next.expiry_date.slice(0, 10);
    }

    if (next.reminder_type === "default") {
      next.reminder_unit = null;
      next.reminder_value = null;
      next.custom_reminders = [];
      next.dnd_start_time = null;
      next.dnd_end_time = null;
    }

    mockPolicies[index] = next;
    return { ...next };
  },
  deletePolicy(policyId: number) {
    const index = mockPolicies.findIndex((item) => item.id === policyId);
    if (index === -1) {
      throw new Error("Policy not found");
    }
    mockPolicies.splice(index, 1);
    mockPolicyReminders.delete(policyId);
    return { detail: "deleted" };
  },
  createFollowup(input: any, organizationId: number) {
    const payload = { ...input, organization_id: organizationId };
    return createMockLead(payload);
  },
  getFollowup(followupId: number) {
    const f = mockLeads.find((l) => l.id === followupId);
    if (!f) throw new Error("not found");
    return enrichMockFollowup(f);
  },
  updateFollowup(followupId: number, updates: any) {
    return patchMockLead(followupId, updates);
  },
  deleteFollowup(followupId: number) {
    const idx = mockLeads.findIndex((l) => l.id === followupId);
    if (idx === -1) throw new Error("not found");
    mockLeads.splice(idx, 1);
    return { detail: "deleted" };
  },
  createLead(input: any) {
    return createMockLead(input);
  },
  patchLead(leadId: number, updates: any) {
    return patchMockLead(leadId, updates);
  },
  renewPolicy(policyId: number, payload?: { new_expiry_date?: string; renewal_notes?: string | null }) {
    const p = mockPolicies.find((x) => x.id === policyId);
    if (!p) throw new Error("Policy not found");
    if (payload?.new_expiry_date) {
      p.expiry_date = payload.new_expiry_date.slice(0, 10);
    } else {
      const target = parseDateOnlyToUTC(p.expiry_date);
      if (target) {
        target.setUTCFullYear(target.getUTCFullYear() + 1);
        p.expiry_date = target.toISOString().slice(0, 10);
      }
    }
    p.status = "active";
    const reminders = buildMockPolicyReminders(policyId, p.expiry_date);
    mockPolicyReminders.set(policyId, reminders);
    return { policy: { ...p }, reminders };
  },
  startLeadWorkflow(leadId: number, body: any) {
    return startMockLeadWorkflow(leadId, body);
  },
  startPolicyWorkflow(policyId: number, body: any) {
    return startMockPolicyWorkflow(policyId, body);
  },
  constructionDashboard() {
    return constructionDashboard;
  },
  medicalDashboard() {
    return medicalDashboard;
  },
  simulateCommand(command: string): CommandPreview {
    const lower = command.toLowerCase();
    if (lower.includes("all") || lower.includes("bulk")) {
      return {
        status: "needs_approval",
        domain: lower.includes("policy") ? "insurance" : "general",
        confidence: 0.96,
        extractedFields: ["audience", "channel"],
        missingFields: [],
        approvalReason: "Bulk customer actions require approval before execution.",
        resultMessage: "Approval request prepared.",
      };
    }
    if (lower.includes("follow up") && !lower.includes("with")) {
      return {
        status: "needs_clarification",
        domain: "general",
        confidence: 0.71,
        extractedFields: ["intent"],
        missingFields: ["assignee"],
        resultMessage: "Need one more detail before executing.",
      };
    }
    return {
      status: "executed",
      domain: lower.includes("policy") ? "insurance" : "general",
      confidence: 0.89,
      extractedFields: ["title", "due_date", "channel"],
      missingFields: [],
      resultMessage: "Task created and routed successfully.",
    };
  },
};
