"""Startup checks for the Telegram bot runtime."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from sqlalchemy import func, select, text

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.atm005 import ContactChannelIdentity
from app.models.core import Organization, User

logger = logging.getLogger(__name__)


def ensure_models_loaded() -> None:
    """Import all ORM models so SQLAlchemy relationship strings resolve."""
    import app.models  # noqa: F401
    import app.models.support_access_sessions  # noqa: F401


async def reset_async_engine_pool() -> None:
    """Dispose pooled connections (e.g. after a temporary event loop was closed)."""
    from app.core.database import engine

    await engine.dispose()
    logger.info("SQLAlchemy async engine pool disposed")


async def verify_telegram_runtime() -> None:
    """Log configuration and verify database connectivity."""
    settings = get_settings()
    parsed = urlparse(settings.database_url.replace("+asyncpg", ""))

    logger.info(
        "Telegram runtime config: token_set=%s default_org_id=%s db_host=%s db_name=%s",
        bool(settings.telegram_agent_bot_token),
        settings.telegram_default_organization_id or "(auto-detect first org)",
        parsed.hostname,
        parsed.path.lstrip("/") or "(unknown)",
    )

    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
        org_count = await session.scalar(select(func.count()).select_from(Organization))
        user_count = await session.scalar(select(func.count()).select_from(User))
        identity_count = await session.scalar(select(func.count()).select_from(ContactChannelIdentity))
        logger.info(
            "Database OK: organizations=%s users=%s telegram_identities=%s",
            org_count,
            user_count,
            identity_count,
        )

        if settings.telegram_default_organization_id:
            org = await session.get(Organization, settings.telegram_default_organization_id)
            if org is None:
                logger.warning(
                    "TELEGRAM_DEFAULT_ORGANIZATION_ID=%s not found in organizations table",
                    settings.telegram_default_organization_id,
                )
        elif not org_count:
            logger.warning("No organizations found — Telegram commands requiring org context will fail")


async def prepare_telegram_runtime() -> None:
    """Reset DB pool and verify connectivity on the active event loop."""
    await reset_async_engine_pool()
    await verify_telegram_runtime()
