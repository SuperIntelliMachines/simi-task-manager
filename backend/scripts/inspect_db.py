import asyncio
import asyncpg
from app.core.config import get_settings

async def main():
    settings = get_settings()
    url = settings.database_url
    # asyncpg accepts postgresql://...
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn=url)
    try:
        v = await conn.fetchrow("SELECT version_num FROM alembic_version;")
        print("alembic_version:", v["version_num"] if v else None)
    except Exception as e:
        print("alembic_version query error:", e)
    for tbl in ["insurance_policies", "insurance_leads", "policy_reminders", "reminder_followup_link"]:
        try:
            r = await conn.fetchval("SELECT to_regclass($1);", f"public.{tbl}")
            print(tbl, "exists:" , bool(r))
        except Exception as e:
            print(tbl, "check error:", e)
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
