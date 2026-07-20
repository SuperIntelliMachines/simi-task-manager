from app.core.database import Base
from app.models import atm005, atm012, atm017, core, verticals, insurance
from app.models import reminder_config, reminder_instance  # noqa: F401 — generic reminder engine
from app.models import reminder_definition  # noqa: F401 — general Reminder Management definitions
from app.models import personal_reminder  # noqa: F401 — Personal Reminders (independent module)
from app.models import reminder_template  # noqa: F401 — Reminder Management templates
from app.models import reminder_history  # noqa: F401 — Reminder History execution log
from app.models import notification  # noqa: F401 — generic in-app notifications
from app.models import support_access_sessions  # noqa: F401 — register SupportAccessSession for Organization mapper
from app.models import rbac, auth_security  # noqa: F401 — RBAC and auth security tables
from app.models import external_organization_mapping  # noqa: F401 — Claims tenant UUID → SIMI org
from app.models import external_entity_mapping  # noqa: F401 — external entity id → SIMI entity_id

__all__ = ["Base"]
