from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.atm017 import AgentSession


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AgentSessionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_clarification_session(
        self,
        *,
        organization_id: int,
        missing_fields: list[str],
        collected_fields: dict | None = None,
        agent_invocation_id: int | None = None,
        expires_in_minutes: int = 30,
    ) -> AgentSession:
        now = utcnow_naive()
        item = AgentSession(
            organization_id=organization_id,
            agent_invocation_id=agent_invocation_id,
            session_type="clarification",
            status="active",
            collected_fields=collected_fields or {},
            missing_fields=missing_fields,
            last_user_reply=None,
            expires_at=now + timedelta(minutes=expires_in_minutes),
            created_at=now,
            updated_at=now,
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def get_session(self, session_id: int) -> AgentSession | None:
        return await self.session.get(AgentSession, session_id)

    async def resume_session_on_reply(
        self,
        *,
        session_id: int,
        user_reply: str,
        extracted_fields: dict,
    ) -> AgentSession:
        item = await self.session.get(AgentSession, session_id)
        if item is None:
            raise ValueError("session not found")

        now = utcnow_naive()
        if item.expires_at is not None and item.expires_at < now:
            item.status = "expired"
            item.updated_at = now
            await self.session.commit()
            await self.session.refresh(item)
            return item

        merged = dict(item.collected_fields or {})
        merged.update(extracted_fields)
        missing = [field for field in (item.missing_fields or []) if field not in merged]

        item.collected_fields = merged
        item.missing_fields = missing
        item.last_user_reply = user_reply
        item.status = "resolved" if not missing else "active"
        item.updated_at = now

        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def expire_stale_sessions(self, organization_id: int) -> int:
        now = utcnow_naive()
        result = await self.session.execute(
            select(AgentSession).where(
                AgentSession.organization_id == organization_id,
                AgentSession.status == "active",
                AgentSession.expires_at.is_not(None),
                AgentSession.expires_at < now,
            )
        )
        rows = list(result.scalars())
        for row in rows:
            row.status = "expired"
            row.updated_at = now

        await self.session.commit()
        return len(rows)
