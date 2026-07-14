"""Due-time helpers for policy reminder queries."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.datetime_utils import utcnow_naive


def due_reminder_at_filter(dialect_name: str, *, now: datetime | None = None):
    """
    SQL filter for due reminders.

    PostgreSQL stores ``reminder_at`` as UTC-naive; compare against DB UTC clock
    so manual SQL using ``(NOW() AT TIME ZONE 'UTC')`` matches the application.
    """
    if dialect_name == "postgresql":
        return lambda column: column <= func.timezone("UTC", func.now())
    cutoff = now if now is not None else utcnow_naive()
    return lambda column: column <= cutoff


async def fetch_db_now(session: AsyncSession) -> datetime:
    """
    Return the database session's current timestamp.

    Use this instead of ``datetime.utcnow()`` or app-local ``datetime.now()`` when
    comparing against ``scheduled_at`` values written with DB-aligned clocks.
    """
    result = await session.execute(select(func.now()))
    value = result.scalar_one()
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    raise TypeError(f"unexpected func.now() type: {type(value)!r}")


async def fetch_due_reminder_cutoff(session: AsyncSession) -> datetime:
    """Return the UTC-naive cutoff timestamp used for due comparisons."""
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        result = await session.execute(select(func.timezone("UTC", func.now())))
        value = result.scalar_one()
        if isinstance(value, datetime):
            return value.replace(tzinfo=None) if value.tzinfo else value
    return await fetch_db_now(session)


async def fetch_db_clock_debug(session: AsyncSession) -> dict[str, str]:
    """Fetch DB clocks for diagnostic logging (PostgreSQL only)."""
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return {
            "python_utc": utcnow_naive().isoformat(),
        }

    from sqlalchemy import text

    result = await session.execute(
        text(
            "SELECT "
            "(NOW() AT TIME ZONE 'UTC') AS utc_now, "
            "NOW() AS session_now, "
            "current_setting('TIMEZONE') AS session_tz"
        )
    )
    row = result.mappings().one()
    return {
        "python_utc": utcnow_naive().isoformat(),
        "db_utc": str(row["utc_now"]),
        "db_session_now": str(row["session_now"]),
        "db_session_tz": str(row["session_tz"]),
    }
