"""Transfer reminder engine table ownership to simi_user. Run as postgres superuser."""
import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

SQL = """
ALTER TABLE IF EXISTS public.reminder_configs OWNER TO simi_user;
ALTER TABLE IF EXISTS public.reminder_instances OWNER TO simi_user;
ALTER SEQUENCE IF EXISTS public.reminder_configs_id_seq OWNER TO simi_user;
ALTER SEQUENCE IF EXISTS public.reminder_instances_id_seq OWNER TO simi_user;
"""


async def main() -> None:
    url = os.getenv(
        "DATABASE_ADMIN_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/simi_task_manager",
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(text(SQL))
    await engine.dispose()
    print("Reminder table ownership transferred to simi_user.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Failed to transfer ownership: {exc}", file=sys.stderr)
        print(
            "Set DATABASE_ADMIN_URL to your postgres superuser URL, or run "
            "backend/sql/transfer_reminder_table_ownership.sql in pgAdmin as postgres.",
            file=sys.stderr,
        )
        sys.exit(1)
