from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.atm012 import AgentInvocation


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AgentInvocationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_invocation(
        self,
        *,
        organization_id: int,
        actor_user_id: int | None,
        agent: str,
        domain: str,
        intent: str,
        confidence: float,
        input_summary: str,
        output_summary: str,
        guardrail_result: str,
        tool_calls: list[str],
        token_usage: dict | None = None,
    ) -> AgentInvocation:
        item = AgentInvocation(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            agent=agent,
            domain=domain,
            intent=intent,
            confidence=confidence,
            input_summary=input_summary,
            output_summary=output_summary,
            guardrail_result=guardrail_result,
            tool_calls=tool_calls,
            token_usage=token_usage,
            created_at=utcnow_naive(),
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item
