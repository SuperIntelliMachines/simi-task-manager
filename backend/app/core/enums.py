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
