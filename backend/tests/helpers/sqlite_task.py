"""SQLite test helpers for models using BigInteger primary keys."""

from __future__ import annotations

from app.services import task_service
from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive


SQLITE_BIGINT_PK_TABLES = frozenset(
    {
        "contacts",
        "insurance_policies",
        "insurance_leads",
        "message_templates",
        "notification_preferences",
        "workflow_templates",
        "workflow_runs",
        "tasks",
        "task_assignments",
        "reminders",
        "policy_reminders",
        "policy_custom_reminders",
        "audit_events",
    }
)


def patch_sqlite_session_bigint_ids(
    async_session,
    *,
    start_id: int = 9800,
    table_names: frozenset[str] | set[str] | None = None,
) -> None:
    """Assign explicit ids on insert for SQLite BigInteger PK tables."""
    counter = {"value": start_id}
    original_add = async_session.add
    allowed_tables = table_names if table_names is not None else None

    def add_with_explicit_id(obj):
        table_name = getattr(obj, "__tablename__", None)
        if getattr(obj, "id", None) is None and table_name is not None:
            if allowed_tables is None or table_name in allowed_tables:
                obj.id = counter["value"]
                counter["value"] += 1
        return original_add(obj)

    async_session.add = add_with_explicit_id  # type: ignore[method-assign]


def patch_task_service_for_sqlite(monkeypatch, *, start_id: int = 9000) -> None:
    """Patch TaskService so task/assignment rows get explicit ids on SQLite."""
    counter = {"task_id": start_id, "assignment_id": start_id + 10_000}

    async def create_task(self, **kwargs):
        from app.models.core import Task

        now = utcnow_naive()
        due_at = normalize_to_utc_naive(kwargs.get("due_at"))
        counter["task_id"] += 1
        item = Task(
            id=counter["task_id"],
            organization_id=kwargs["organization_id"],
            title=kwargs["title"],
            description=kwargs.get("description"),
            domain=kwargs.get("domain", "general"),
            status="open",
            priority=kwargs.get("priority") or "medium",
            due_at=due_at,
            created_at=now,
            updated_at=now,
        )
        self.session.add(item)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def assign_task(self, **kwargs):
        from app.models.core import Task, TaskAssignment

        item = await self.session.get(Task, kwargs["task_id"])
        if item is None:
            raise ValueError("task not found")

        now = utcnow_naive()
        counter["assignment_id"] += 1
        assignment = TaskAssignment(
            id=counter["assignment_id"],
            organization_id=kwargs["organization_id"],
            task_id=item.id,
            user_id=kwargs.get("user_id"),
            contact_id=kwargs.get("contact_id"),
            status="assigned",
            assigned_at=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(assignment)
        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    monkeypatch.setattr(task_service.TaskService, "create_task", create_task)
    monkeypatch.setattr(task_service.TaskService, "assign_task", assign_task)
