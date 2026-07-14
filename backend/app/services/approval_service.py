from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.atm017 import ApprovalRequest, AuditEvent, OutboundMessage


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _audit(
    *,
    session: AsyncSession,
    organization_id: int,
    actor_user_id: int | None,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
) -> None:
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            created_at=utcnow_naive(),
        )
    )


class ApprovalService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_requests(self, organization_id: int) -> list[ApprovalRequest]:
        result = await self.session.execute(
            select(ApprovalRequest)
            .where(ApprovalRequest.organization_id == organization_id)
            .order_by(ApprovalRequest.created_at.desc())
        )
        return list(result.scalars())

    async def create_request(
        self,
        *,
        organization_id: int,
        requested_by_user_id: int | None,
        proposed_action: dict,
        reason: str | None,
        expires_at: datetime | None = None,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            organization_id=organization_id,
            requested_by_user_id=requested_by_user_id,
            status="pending",
            reason=reason,
            proposed_action=proposed_action,
            expires_at=expires_at,
            created_at=utcnow_naive(),
            updated_at=utcnow_naive(),
        )
        self.session.add(request)
        await self.session.flush()

        _audit(
            session=self.session,
            organization_id=organization_id,
            actor_user_id=requested_by_user_id,
            event_type="approval.created",
            entity_type="approval_request",
            entity_id=str(request.id),
            payload={"reason": reason},
        )

        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def approve_request(self, request_id: int, approver_user_id: int | None) -> ApprovalRequest:
        request = await self.session.get(ApprovalRequest, request_id)
        if request is None:
            raise ValueError("approval request not found")

        now = utcnow_naive()
        if request.status == "approved" and request.executed_at is not None:
            return request

        if request.status != "pending":
            return request

        if request.expires_at is not None and request.expires_at < now:
            request.status = "expired"
            request.updated_at = now
            await self.session.commit()
            await self.session.refresh(request)
            return request

        request.status = "approved"
        request.approved_by_user_id = approver_user_id
        request.decisioned_at = now
        request.updated_at = now

        if request.executed_at is None:
            await self._execute_proposed_action(request)
            request.executed_at = now

        _audit(
            session=self.session,
            organization_id=request.organization_id,
            actor_user_id=approver_user_id,
            event_type="approval.approved",
            entity_type="approval_request",
            entity_id=str(request.id),
            payload={"executed": request.executed_at is not None},
        )

        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def reject_request(
        self,
        request_id: int,
        rejector_user_id: int | None,
        notes: str | None,
    ) -> ApprovalRequest:
        request = await self.session.get(ApprovalRequest, request_id)
        if request is None:
            raise ValueError("approval request not found")

        if request.status != "pending":
            return request

        request.status = "rejected"
        request.rejected_by_user_id = rejector_user_id
        request.decision_notes = notes
        request.decisioned_at = utcnow_naive()
        request.updated_at = utcnow_naive()

        _audit(
            session=self.session,
            organization_id=request.organization_id,
            actor_user_id=rejector_user_id,
            event_type="approval.rejected",
            entity_type="approval_request",
            entity_id=str(request.id),
            payload={"notes": notes},
        )

        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def expire_old_requests(self, organization_id: int) -> int:
        now = utcnow_naive()
        result = await self.session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.organization_id == organization_id,
                ApprovalRequest.status == "pending",
                ApprovalRequest.expires_at.is_not(None),
                ApprovalRequest.expires_at < now,
            )
        )
        rows = list(result.scalars())
        for item in rows:
            item.status = "expired"
            item.updated_at = now
            _audit(
                session=self.session,
                organization_id=item.organization_id,
                actor_user_id=None,
                event_type="approval.expired",
                entity_type="approval_request",
                entity_id=str(item.id),
                payload={},
            )

        await self.session.commit()
        return len(rows)

    async def _execute_proposed_action(self, request: ApprovalRequest) -> None:
        action = request.proposed_action or {}
        action_type = action.get("action_type")
        payload = action.get("payload", {})

        if action_type == "send_bulk_reminder":
            recipients = payload.get("recipients", [])
            body = payload.get("body", "")
            channel = payload.get("channel", "whatsapp")
            for recipient in recipients:
                self.session.add(
                    OutboundMessage(
                        organization_id=request.organization_id,
                        task_id=None,
                        channel=channel,
                        recipient=recipient,
                        body=body,
                        status="queued",
                        created_at=utcnow_naive(),
                        updated_at=utcnow_naive(),
                    )
                )

        _audit(
            session=self.session,
            organization_id=request.organization_id,
            actor_user_id=request.approved_by_user_id,
            event_type="approval.executed",
            entity_type="approval_request",
            entity_id=str(request.id),
            payload={"action_type": action_type},
        )
