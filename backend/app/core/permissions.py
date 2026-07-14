"""Canonical permission codes for SIMI RBAC."""

from __future__ import annotations

# Insurance
INSURANCE_VIEW = "insurance:view"
INSURANCE_CREATE = "insurance:create"
INSURANCE_UPDATE = "insurance:update"
INSURANCE_DELETE = "insurance:delete"

# Claims
CLAIMS_VIEW = "claims:view"
CLAIMS_CREATE = "claims:create"
CLAIMS_UPDATE = "claims:update"
CLAIMS_ASSIGN = "claims:assign"
CLAIMS_CLOSE = "claims:close"

# Reminders
REMINDERS_VIEW = "reminders:view"
REMINDERS_CREATE = "reminders:create"
REMINDERS_UPDATE = "reminders:update"
REMINDERS_DELETE = "reminders:delete"
REMINDERS_PROCESS = "reminders:process"

# Leads
LEADS_VIEW = "leads:view"
LEADS_CREATE = "leads:create"
LEADS_UPDATE = "leads:update"
LEADS_DELETE = "leads:delete"

# Bid Management System
BMS_VIEW = "bms:view"
BMS_CREATE = "bms:create"
BMS_UPDATE = "bms:update"
BMS_DELETE = "bms:delete"
BMS_ASSIGN = "bms:assign"

# AI Agents
AGENTS_VIEW = "agents:view"
AGENTS_CREATE = "agents:create"
AGENTS_UPDATE = "agents:update"
AGENTS_DELETE = "agents:delete"
AGENTS_INVOKE = "agents:invoke"

# Users
USERS_VIEW = "users:view"
USERS_CREATE = "users:create"
USERS_UPDATE = "users:update"
USERS_DELETE = "users:delete"
USERS_INVITE = "users:invite"

# Admin / platform
ADMIN_VIEW = "admin:view"
ADMIN_CREATE = "admin:create"
ADMIN_UPDATE = "admin:update"
ADMIN_DELETE = "admin:delete"
ADMIN_ONBOARD = "admin:onboard"
ADMIN_INVITE = "admin:invite"

# Tasks
TASKS_VIEW = "tasks:view"
TASKS_CREATE = "tasks:create"
TASKS_UPDATE = "tasks:update"
TASKS_DELETE = "tasks:delete"
TASKS_COMPLETE = "tasks:complete"

# Channels & templates
CHANNELS_VIEW = "channels:view"
CHANNELS_CREATE = "channels:create"
CHANNELS_UPDATE = "channels:update"
CHANNELS_TEST = "channels:test"

TEMPLATES_VIEW = "templates:view"
TEMPLATES_CREATE = "templates:create"
TEMPLATES_UPDATE = "templates:update"
TEMPLATES_APPROVE = "templates:approve"

APPROVALS_VIEW = "approvals:view"
APPROVALS_APPROVE = "approvals:approve"
APPROVALS_REJECT = "approvals:reject"

ALL_PERMISSIONS: tuple[str, ...] = (
    INSURANCE_VIEW,
    INSURANCE_CREATE,
    INSURANCE_UPDATE,
    INSURANCE_DELETE,
    CLAIMS_VIEW,
    CLAIMS_CREATE,
    CLAIMS_UPDATE,
    CLAIMS_ASSIGN,
    CLAIMS_CLOSE,
    REMINDERS_VIEW,
    REMINDERS_CREATE,
    REMINDERS_UPDATE,
    REMINDERS_DELETE,
    REMINDERS_PROCESS,
    LEADS_VIEW,
    LEADS_CREATE,
    LEADS_UPDATE,
    LEADS_DELETE,
    BMS_VIEW,
    BMS_CREATE,
    BMS_UPDATE,
    BMS_DELETE,
    BMS_ASSIGN,
    AGENTS_VIEW,
    AGENTS_CREATE,
    AGENTS_UPDATE,
    AGENTS_DELETE,
    AGENTS_INVOKE,
    USERS_VIEW,
    USERS_CREATE,
    USERS_UPDATE,
    USERS_DELETE,
    USERS_INVITE,
    ADMIN_VIEW,
    ADMIN_CREATE,
    ADMIN_UPDATE,
    ADMIN_DELETE,
    ADMIN_ONBOARD,
    ADMIN_INVITE,
    TASKS_VIEW,
    TASKS_CREATE,
    TASKS_UPDATE,
    TASKS_DELETE,
    TASKS_COMPLETE,
    CHANNELS_VIEW,
    CHANNELS_CREATE,
    CHANNELS_UPDATE,
    CHANNELS_TEST,
    TEMPLATES_VIEW,
    TEMPLATES_CREATE,
    TEMPLATES_UPDATE,
    TEMPLATES_APPROVE,
    APPROVALS_VIEW,
    APPROVALS_APPROVE,
    APPROVALS_REJECT,
)

PLATFORM_ROLE_NAMES = frozenset(
    {
        "platform_admin",
        "support_engineer",
        "implementation_manager",
    }
)
