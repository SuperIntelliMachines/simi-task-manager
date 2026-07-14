"""Grant simi_user access to policy_custom_reminders. Run as postgres superuser."""
import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    # Prefer explicit admin URL; fall back to postgres on localhost.
    url = os.getenv(
        "DATABASE_ADMIN_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/simi_task_manager",
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.policy_custom_reminders TO simi_user;
                GRANT USAGE, SELECT ON SEQUENCE public.policy_custom_reminders_id_seq TO simi_user;
                """
            )
        )
    await engine.dispose()
    print("Grants applied successfully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Failed to apply grants: {exc}", file=sys.stderr)
        print(
            "Run backend/sql/grant_policy_custom_reminders.sql manually in pgAdmin as postgres.",
            file=sys.stderr,
        )
        sys.exit(1)
