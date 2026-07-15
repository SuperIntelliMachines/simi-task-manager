"""Grant simi_user access to personal_reminders. Run as postgres superuser."""
import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    url = os.getenv(
        "DATABASE_ADMIN_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/simi_task_manager",
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                GRANT SELECT, INSERT, UPDATE, DELETE
                  ON TABLE public.personal_reminders TO simi_user;
                """
            )
        )
    await engine.dispose()
    print("Grants applied successfully for personal_reminders.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Failed to apply grants: {exc}", file=sys.stderr)
        print(
            "Run backend/sql/grant_personal_reminders.sql manually in pgAdmin as postgres.",
            file=sys.stderr,
        )
        sys.exit(1)
