"""Check policy_custom_reminders table access for the app DB user."""
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    url = "postgresql+asyncpg://simi_user:simi_manager@localhost:5432/simi_task_manager"
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        owner = await conn.execute(
            text(
                "SELECT tableowner FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename = 'policy_custom_reminders'"
            )
        )
        print("owner:", owner.scalar())
        try:
            count = await conn.execute(text("SELECT COUNT(*) FROM policy_custom_reminders"))
            print("count:", count.scalar())
        except Exception as exc:
            print("select error:", exc)
        policies = await conn.execute(
            text("SELECT COUNT(*) FROM insurance_policies WHERE organization_id = 607")
        )
        print("policies org 607:", policies.scalar())
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
