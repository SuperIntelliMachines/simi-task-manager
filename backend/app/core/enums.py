from enum import Enum


class UserRole(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    SUPPORT_ENGINEER = "support_engineer"
    IMPLEMENTATION_MANAGER = "implementation_manager"
    TENANT_USER = "tenant_user"


class ReminderAnchorType(str, Enum):
    """How a reminder config selects its scheduling anchor.

    Values are module-agnostic:
    - DATE: relative to an entity datetime field (e.g. expiry, due date)
    - WORKFLOW: relative to entering a workflow/status stage
    """

    DATE = "date"
    WORKFLOW = "workflow"


class ReminderOffsetDirection(str, Enum):
    """Whether the offset is applied before or after the resolved anchor."""

    BEFORE = "before"
    AFTER = "after"


# Generic default key for DATE anchors — resolvers map this to the entity's primary datetime.
DEFAULT_REMINDER_ANCHOR_KEY = "anchor_date"


class ReminderStopCondition(str, Enum):
    """Generic stop conditions evaluated by the engine and/or module resolvers."""

    NEVER = "never"
    ENTITY_INELIGIBLE = "entity_ineligible"
    WORKFLOW_STATUS_CHANGED = "workflow_status_changed"
    END_DATE_REACHED = "end_date_reached"
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"


DEFAULT_REMINDER_STOP_CONDITION = ReminderStopCondition.ENTITY_INELIGIBLE.value


class ReminderGenerationMode(str, Enum):
    """How reminder_instances are created for a config.

    - PAYLOAD: caller supplies schedule + recipients + template data; instances are
      materialized when the config is saved (no module resolver).
    - RESOLVER: engine discovers entities and anchors via ReminderEntityResolver
      (Insurance relative reminders, org-level rules, etc.).
    """

    PAYLOAD = "payload"
    RESOLVER = "resolver"


DEFAULT_REMINDER_GENERATION_MODE = ReminderGenerationMode.RESOLVER.value

REMINDER_OFFSET_UNITS = frozenset({"hours", "days", "weeks", "months"})
