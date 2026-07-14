"""User-facing labels for organization dependency tables.

Add one entry here when a new module introduces organization-scoped tables.
Unknown tables are never exposed to clients; they map to RELATED_BUSINESS_DATA_LABEL.
"""

from __future__ import annotations

RELATED_BUSINESS_DATA_LABEL = "Related Business Data"

DEPENDENCY_LABELS: dict[str, str] = {
    "users": "Users",
    "organization_memberships": "Organization Memberships",
    "contacts": "Contacts",
    "contact_channel_identities": "Contact Channels",
    "tasks": "Tasks",
    "task_assignments": "Task Assignments",
    "reminders": "Reminders",
    "reminder_attempts": "Reminder Attempts",
    "reminder_configs": "Reminder Configurations",
    "reminder_instances": "Reminders",
    "policy_reminders": "Policy Reminders",
    "message_templates": "Message Templates",
    "notification_preferences": "Notifications",
    "outbound_messages": "Outbound Messages",
    "inbound_messages": "Inbound Messages",
    "audit_events": "Audit History",
    "workflow_templates": "Workflow Templates",
    "workflow_runs": "Workflow Runs",
    "insurance_leads": "Insurance Leads",
    "insurance_policies": "Insurance Policies",
    "claims": "Claims",
    "agent_definitions": "AI Agents",
    "agent_invocations": "Agent Activity",
    "agent_sessions": "Agent Sessions",
    "approval_requests": "Approval Requests",
    "channel_connections": "Channel Connections",
    "construction_projects": "Construction Projects",
    "bms_bids": "Bids",
    "hr_employees": "Employees",
    "crm_accounts": "CRM Accounts",
}


def label_for_table(table_name: str) -> str:
    """Return a user-friendly label; never return the raw table name."""
    return DEPENDENCY_LABELS.get(table_name, RELATED_BUSINESS_DATA_LABEL)


def build_dependency_items(
    blocking: list[dict[str, object]],
) -> list[dict[str, object]]:
    """
    Convert technical blocking rows into aggregated user-facing dependency items.

    Multiple tables that share the same label are merged (counts summed).
    """
    aggregated: dict[str, int] = {}
    for item in blocking:
        table = str(item.get("table") or "")
        count = int(item.get("count") or 0)
        if count <= 0:
            continue
        label = label_for_table(table)
        aggregated[label] = aggregated.get(label, 0) + count

    return [
        {"label": label, "count": count}
        for label, count in sorted(aggregated.items(), key=lambda pair: (-pair[1], pair[0]))
    ]


def organization_dependency_conflict_detail(
    dependencies: list[dict[str, object]],
    *,
    message: str | None = None,
) -> dict[str, object]:
    return {
        "error": "organization_has_dependencies",
        "message": message
        or "This organization cannot be deleted because it still contains related business data.",
        "dependencies": dependencies,
    }
