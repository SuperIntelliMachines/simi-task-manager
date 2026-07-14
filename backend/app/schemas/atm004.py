from datetime import datetime

from pydantic import BaseModel


class TaskCreateBody(BaseModel):
    organization_id: int
    title: str
    description: str | None = None
    due_at: datetime | None = None
    domain: str = "general"
    actor_user_id: int | None = None
    priority: str | None = "medium"


class TaskPatchBody(BaseModel):
    title: str | None = None
    description: str | None = None
    due_at: datetime | None = None
    domain: str | None = None
    status: str | None = None
    actor_user_id: int | None = None
    priority: str | None = None


class TaskCompleteBody(BaseModel):
    actor_user_id: int | None = None
    cancel_future_reminders: bool = True


class TaskSnoozeBody(BaseModel):
    due_at: datetime
    actor_user_id: int | None = None


class ReminderCreateBody(BaseModel):
    organization_id: int
    task_id: int
    dedupe_key: str
    scheduled_for: datetime
    actor_user_id: int | None = None


class ReminderAckBody(BaseModel):
    actor_user_id: int | None = None
