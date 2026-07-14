from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.atm017 import AuditEvent


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def write_audit_event(
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
