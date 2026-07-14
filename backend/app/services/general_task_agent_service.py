from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Contact, OrganizationMembership, Task, TaskAssignment, User
from app.schemas.atm012 import AgentCommandInput, AgentExecutionResult, AgentStructuredResponse, ClarificationRequest, CreatedEntity
from app.services.reminder_service import ReminderService
from app.services.task_service import TaskService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class GeneralTaskAgentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_service = TaskService(session)
        self.reminder_service = ReminderService(session)

    async def execute(
        self,
        *,
        command: AgentCommandInput,
        response: AgentStructuredResponse,
        result: AgentExecutionResult,
    ) -> AgentExecutionResult:
        created_entities: list[CreatedEntity] = []
        user_message = result.user_message or response.user_response or result.summary
        summary = result.summary or response.user_response or response.entities.get("summary")

        for action in response.proposed_actions:
            if action.tool_name == "create_reminder":
                task = await self.task_service.create_task(
                    organization_id=command.organization_id,
                    title=action.args["title"],
                    description=action.args.get("description"),
                    due_at=self._parse_datetime(action.args.get("due_at")),
                    domain="general",
                    actor_user_id=command.actor_user_id,
                )
                created_entities.append(CreatedEntity(type="task", id=str(task.id)))
                reminder = await self.reminder_service.create_reminder(
                    organization_id=command.organization_id,
                    task_id=task.id,
                    dedupe_key=self._dedupe_key(command, action.args["title"]),
                    scheduled_for=self._parse_datetime(action.args["scheduled_for"]),
                    actor_user_id=command.actor_user_id,
                )
                created_entities.append(CreatedEntity(type="reminder", id=str(reminder.id)))
            elif action.tool_name == "create_task":
                task = await self.task_service.create_task(
                    organization_id=command.organization_id,
                    title=action.args["title"],
                    description=action.args.get("description"),
                    due_at=self._parse_datetime(action.args.get("due_at")),
                    domain="general",
                    actor_user_id=command.actor_user_id,
                )
                created_entities.append(CreatedEntity(type="task", id=str(task.id)))
            elif action.tool_name == "assign_task":
                assignee = await self._resolve_assignee(
                    organization_id=command.organization_id,
                    assignee_name=action.args.get("assignee_name"),
                )
                if isinstance(assignee, AgentExecutionResult):
                    return assignee
                task = await self.task_service.create_task(
                    organization_id=command.organization_id,
                    title=action.args["title"],
                    description=action.args.get("description"),
                    due_at=self._parse_datetime(action.args.get("due_at")),
                    domain="general",
                    actor_user_id=command.actor_user_id,
                )
                created_entities.append(CreatedEntity(type="task", id=str(task.id)))
                assignment = await self.task_service.assign_task(
                    task_id=task.id,
                    organization_id=command.organization_id,
                    user_id=assignee.get("user_id"),
                    contact_id=assignee.get("contact_id"),
                    actor_user_id=command.actor_user_id,
                )
                created_entities.append(CreatedEntity(type="task_assignment", id=str(assignment.id)))
            elif action.tool_name == "complete_task":
                task = await self._resolve_task_for_action(
                    organization_id=command.organization_id,
                    actor_user_id=command.actor_user_id,
                    task_id=action.args.get("task_id"),
                    title_hint=action.args.get("task_title"),
                    permission_action="complete",
                )
                if isinstance(task, AgentExecutionResult):
                    return task
                updated = await self.task_service.complete_task(task.id, actor_user_id=command.actor_user_id)
                created_entities.append(CreatedEntity(type="task", id=str(updated.id)))
            elif action.tool_name == "snooze_task":
                task = await self._resolve_task_for_action(
                    organization_id=command.organization_id,
                    actor_user_id=command.actor_user_id,
                    task_id=action.args.get("task_id"),
                    title_hint=action.args.get("task_title"),
                    permission_action="snooze",
                )
                if isinstance(task, AgentExecutionResult):
                    return task
                updated = await self.task_service.snooze_task(
                    task.id,
                    due_at=self._parse_datetime(action.args["due_at"]),
                    actor_user_id=command.actor_user_id,
                )
                created_entities.append(CreatedEntity(type="task", id=str(updated.id)))
            elif action.tool_name == "summarize_tasks":
                tasks = await self.task_service.list_tasks(
                    organization_id=command.organization_id,
                    status=action.args.get("status"),
                    domain="general",
                )
                summary = self._summarize_tasks(tasks)
                user_message = summary
            elif action.tool_name == "list_overdue_tasks":
                tasks = await self.task_service.list_tasks(
                    organization_id=command.organization_id,
                    status=action.args.get("status"),
                    domain="general",
                )
                overdue = [task for task in tasks if task.due_at and task.due_at < utcnow_naive() and task.status != "completed"]
                summary = self._summarize_tasks(overdue, prefix="Overdue tasks")
                user_message = summary

        return result.model_copy(
            update={
                "created_entities": created_entities,
                "summary": summary,
                "user_message": user_message,
            }
        )

    async def _resolve_assignee(
        self,
        *,
        organization_id: int,
        assignee_name: str | None,
    ) -> dict[str, int | None] | AgentExecutionResult:
        if not assignee_name:
            return self._clarification("Please specify who should be assigned this task.", ["assignee"])

        normalized = assignee_name.lower()
        users_result = await self.session.execute(
            select(User).where(
                User.organization_id == organization_id,
                or_(User.email.ilike(f"{normalized}%"), User.email.ilike(f"%{normalized}%")),
            )
        )
        contacts_result = await self.session.execute(
            select(Contact).where(
                Contact.organization_id == organization_id,
                Contact.name.ilike(f"%{assignee_name}%"),
            )
        )
        users = list(users_result.scalars())
        contacts = list(contacts_result.scalars())

        if len(users) + len(contacts) == 0:
            return self._clarification(f"I could not find an assignee named {assignee_name}.", ["assignee"])
        if len(users) + len(contacts) > 1:
            return self._clarification(
                f"I found multiple matches for {assignee_name}. Please specify the exact user or contact.",
                ["assignee"],
            )
        if users:
            return {"user_id": users[0].id, "contact_id": None}
        return {"user_id": None, "contact_id": contacts[0].id}

    async def _resolve_task_for_action(
        self,
        *,
        organization_id: int,
        actor_user_id: int | None,
        task_id: int | None,
        title_hint: str | None,
        permission_action: str,
    ) -> Task | AgentExecutionResult:
        task: Task | None = None
        if task_id is not None:
            task = await self.session.get(Task, int(task_id))
            if task is None or task.organization_id != organization_id:
                return self._failed("The requested task was not found in this tenant.")
        elif title_hint:
            result = await self.session.execute(
                select(Task).where(
                    Task.organization_id == organization_id,
                    Task.title.ilike(f"%{title_hint}%"),
                    Task.status.in_(["open", "assigned", "snoozed"]),
                )
            )
            tasks = list(result.scalars())
            if not tasks:
                return self._clarification(f"I could not find a task matching '{title_hint}'.", ["task"])
            if len(tasks) > 1:
                return self._clarification(f"I found multiple tasks matching '{title_hint}'. Please specify which one.", ["task"])
            task = tasks[0]
        else:
            return self._clarification("Please specify which task to update.", ["task"])

        if permission_action == "complete":
            permission_error = await self._check_completion_permission(task, actor_user_id)
            if permission_error is not None:
                return permission_error
        return task

    async def _check_completion_permission(self, task: Task, actor_user_id: int | None) -> AgentExecutionResult | None:
        if actor_user_id is None:
            return None

        assignments_result = await self.session.execute(
            select(TaskAssignment).where(TaskAssignment.task_id == task.id)
        )
        assignments = list(assignments_result.scalars())
        assigned_user_ids = {assignment.user_id for assignment in assignments if assignment.user_id is not None}
        if not assigned_user_ids or actor_user_id in assigned_user_ids:
            return None

        membership_result = await self.session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == task.organization_id,
                OrganizationMembership.user_id == actor_user_id,
            )
        )
        membership = membership_result.scalar_one_or_none()
        if membership is not None and membership.role in {"owner", "admin"}:
            return None

        return self._failed("You do not have permission to complete another user's task.")

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)

    def _dedupe_key(self, command: AgentCommandInput, title: str) -> str:
        digest = sha1(f"{command.organization_id}:{command.command_text}:{title}".encode("utf-8")).hexdigest()[:12]
        return f"agent-reminder-{digest}"

    def _summarize_tasks(self, tasks: list[Task], prefix: str = "Task summary") -> str:
        if not tasks:
            return f"{prefix}: no matching tasks."
        rendered = ", ".join(f"#{task.id} {task.title} ({task.status})" for task in tasks)
        return f"{prefix}: {rendered}"

    def _clarification(self, question: str, missing_fields: list[str]) -> AgentExecutionResult:
        return AgentExecutionResult(
            status="needs_clarification",
            agent_key="general_task_agent",
            domain="general",
            intent="follow_up",
            confidence=0.5,
            summary=None,
            created_entities=[],
            missing_fields=missing_fields,
            approval_request_id=None,
            user_message=None,
            structured_response=None,
            clarification=ClarificationRequest(question=question, missing_fields=missing_fields),
            approval_required=None,
        )

    def _failed(self, message: str) -> AgentExecutionResult:
        return AgentExecutionResult(
            status="failed",
            agent_key="general_task_agent",
            domain="general",
            intent="follow_up",
            confidence=0.5,
            summary=message,
            created_entities=[],
            missing_fields=[],
            approval_request_id=None,
            user_message=message,
            structured_response=None,
            clarification=None,
            approval_required=None,
        )
