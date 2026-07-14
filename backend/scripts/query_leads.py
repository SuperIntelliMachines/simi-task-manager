import asyncio
import asyncpg
from app.core.config import get_settings

async def main():
    settings = get_settings()
    url = settings.database_url
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn=url)
    try:
        rows = await conn.fetch('SELECT id, organization_id, contact_name, status, followup_due_at, demo_logged_at, created_at FROM insurance_leads ORDER BY created_at DESC LIMIT 20')
        print('leads count:', len(rows))
        for r in rows:
            print(dict(r))
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
