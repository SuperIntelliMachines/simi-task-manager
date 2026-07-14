from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.atm017 import NotificationPreference


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _is_within_quiet_hours(current_hour: int, start: int, end: int) -> bool:
    if start <= end:
        return start <= current_hour < end
    return current_hour >= start or current_hour < end


class NotificationPreferenceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_preferences(self, organization_id: int) -> list[NotificationPreference]:
        result = await self.session.execute(
            select(NotificationPreference)
            .where(NotificationPreference.organization_id == organization_id)
            .order_by(NotificationPreference.updated_at.desc())
        )
        return list(result.scalars())

    async def update_preference(self, preference_id: int, updates: dict) -> NotificationPreference:
        item = await self.session.get(NotificationPreference, preference_id)
        if item is None:
            raise ValueError("preference not found")

        for key, value in updates.items():
            setattr(item, key, value)
        item.updated_at = utcnow_naive()

        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def choose_channel(
        self,
        *,
        organization_id: int,
        purpose: str,
        user_id: int | None = None,
        contact_id: int | None = None,
        current_hour: int,
        urgent: bool = False,
    ) -> str | None:
        result = await self.session.execute(
            select(NotificationPreference).where(
                NotificationPreference.organization_id == organization_id,
                NotificationPreference.purpose == purpose,
                NotificationPreference.user_id == user_id,
                NotificationPreference.contact_id == contact_id,
            )
        )
        pref = result.scalar_one_or_none()
        if pref is None:
            return None

        if pref.opt_out:
            return None

        if (
            not urgent
            and pref.quiet_hours_start is not None
            and pref.quiet_hours_end is not None
            and _is_within_quiet_hours(current_hour, pref.quiet_hours_start, pref.quiet_hours_end)
        ):
            return pref.fallback_channel

        return pref.preferred_channel
