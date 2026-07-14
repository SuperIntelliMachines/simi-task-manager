from collections.abc import AsyncGenerator

import sys
import asyncio

import pytest
import os

# Use selector event loop on Windows to avoid Proactor/asyncpg issues in tests
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool, event
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.core.config import get_settings
from app.core.database import Base, engine
import app.models as app_models  # noqa: F401


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture
async def authed_async_client(async_session) -> AsyncGenerator[tuple[AsyncClient, dict[str, str], int], None]:
    """HTTP client with platform-admin auth headers and organization id."""
    from app.core.database import get_db_session
    from tests.helpers.auth import seed_authenticated_context

    org, _user, headers = await seed_authenticated_context(async_session)

    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client, headers, org.id
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db():
    class DummyDB:
        pass

    return DummyDB()


@pytest.fixture(scope="session", autouse=True)
async def dispose_shared_engine() -> AsyncGenerator[None, None]:
    # dispose the app engine (may be replaced by prepare_test_database)
    yield
    from app.core import database as core_db

    if hasattr(core_db, "engine") and core_db.engine is not None:
        await core_db.engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def prepare_test_database() -> AsyncGenerator[None, None]:
    """Create all tables at test session start and drop them at the end.

    This ensures the TestClient endpoints can access tables even if they
    trigger DB activity before per-test transactional fixtures run.
    """
    # Use a local sqlite test database unless TEST_DATABASE_URL is provided
    test_db_url = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    test_engine = create_async_engine(test_db_url, poolclass=pool.NullPool)

    # Replace app core database engine/session factory so the app uses test engine
    import app.core.database as core_db

    core_db.engine = test_engine
    core_db.AsyncSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    # create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(core_db.Base.metadata.create_all)

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        from app.seeds.rbac_seed import seed_rbac

        await seed_rbac(session)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(core_db.Base.metadata.drop_all)


@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    # use the test engine configured in prepare_test_database
    import app.core.database as core_db
    test_engine = core_db.engine
    async with test_engine.connect() as connection:
        # begin a top-level transaction
        await connection.begin()

        # ensure tables exist for the session (created once at session scope)
        # schema is created in prepare_test_database fixture

        session_factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            class_=AsyncSession,
        )

        # event listener to restart SAVEPOINTs after commits
        @event.listens_for(SyncSession, "after_transaction_end")
        def _restart_savepoint(session, transaction):
            if transaction.nested and not transaction._parent:
                session.begin_nested()

        async with session_factory() as session:
            # start a nested transaction (SAVEPOINT) for test isolation
            await session.begin_nested()
            yield session

        # rollback the top-level transaction to clean state
        await connection.rollback()

    # don't dispose the shared test engine here; dispose_shared_engine will handle it
    return
