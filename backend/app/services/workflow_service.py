from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import WorkflowRun, WorkflowTemplate
from app.services.audit_service import write_audit_event


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class WorkflowService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_workflow_template(
        self,
        *,
        organization_id: int,
        name: str,
        definition: str,
        version: int = 1,
        actor_user_id: int | None = None,
    ) -> WorkflowTemplate:
        now = utcnow_naive()
        item = WorkflowTemplate(
            organization_id=organization_id,
            name=name,
            version=version,
            definition=definition,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.session.add(item)
        await self.session.flush()
        await write_audit_event(
            session=self.session,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            event_type="workflow_template.created",
            entity_type="workflow_template",
            entity_id=str(item.id),
            payload={"name": name},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def start_workflow_run(
        self,
        *,
        organization_id: int,
        workflow_template_id: int,
        task_id: int | None,
        current_step: str | None = None,
        actor_user_id: int | None = None,
    ) -> WorkflowRun:
        now = utcnow_naive()
        item = WorkflowRun(
            organization_id=organization_id,
            workflow_template_id=workflow_template_id,
            task_id=task_id,
            status="running",
            current_step=current_step,
            state_payload=None,
            started_at=now,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        self.session.add(item)
        await self.session.flush()
        await write_audit_event(
            session=self.session,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            event_type="workflow_run.started",
            entity_type="workflow_run",
            entity_id=str(item.id),
            payload={"workflow_template_id": workflow_template_id},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def advance_workflow_state(
        self,
        workflow_run_id: int,
        current_step: str,
        state_payload: str | None,
        actor_user_id: int | None = None,
    ) -> WorkflowRun:
        item = await self.session.get(WorkflowRun, workflow_run_id)
        if item is None:
            raise ValueError("workflow run not found")

        item.current_step = current_step
        item.state_payload = state_payload
        item.updated_at = utcnow_naive()

        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="workflow_run.advanced",
            entity_type="workflow_run",
            entity_id=str(item.id),
            payload={"current_step": current_step},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def complete_workflow(self, workflow_run_id: int, actor_user_id: int | None = None) -> WorkflowRun:
        item = await self.session.get(WorkflowRun, workflow_run_id)
        if item is None:
            raise ValueError("workflow run not found")

        now = utcnow_naive()
        item.status = "completed"
        item.completed_at = now
        item.updated_at = now

        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="workflow_run.completed",
            entity_type="workflow_run",
            entity_id=str(item.id),
            payload={},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def cancel_workflow(self, workflow_run_id: int, actor_user_id: int | None = None) -> WorkflowRun:
        item = await self.session.get(WorkflowRun, workflow_run_id)
        if item is None:
            raise ValueError("workflow run not found")

        item.status = "canceled"
        item.updated_at = utcnow_naive()

        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="workflow_run.canceled",
            entity_type="workflow_run",
            entity_id=str(item.id),
            payload={},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item
