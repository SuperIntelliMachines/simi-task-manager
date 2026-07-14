from fastapi import APIRouter, HTTPException
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal

router = APIRouter()
settings = get_settings()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="database not ready") from exc

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.ping()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="redis not ready") from exc
    finally:
        await redis.aclose()

    return {"status": "ready"}
