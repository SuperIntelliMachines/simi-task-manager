from datetime import datetime

import pytest
from sqlalchemy import func, select

from app.utils.reminder_query_time import fetch_db_now


@pytest.mark.asyncio
async def test_fetch_db_now_returns_naive_datetime(async_session):
    now = await fetch_db_now(async_session)
    assert isinstance(now, datetime)
    assert now.tzinfo is None


@pytest.mark.asyncio
async def test_fetch_db_now_matches_sql_func_now(async_session):
    db_now = await fetch_db_now(async_session)
    sql_now = (await async_session.execute(select(func.now()))).scalar_one()
    if isinstance(sql_now, datetime) and sql_now.tzinfo is not None:
        sql_now = sql_now.replace(tzinfo=None)
    assert isinstance(sql_now, datetime)
    assert abs((db_now - sql_now).total_seconds()) < 2
