---
title: "[ATM-002] [Task] Project Foundation Using GyantrAI Stack"
labels: [task, backend, frontend, infrastructure, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-002 - Project Foundation Using GyantrAI Stack

## Objective

Create the application foundation using the same stack conventions as GyantrAI: FastAPI, Python 3.11, SQLAlchemy async, Alembic, PostgreSQL, Redis/Celery, React 18, TypeScript, Vite, Tailwind, Radix/shadcn-style components, TanStack Query, pytest, Vitest, and Playwright.

## Implementation Steps

1. Create `backend/` FastAPI project structure:
   - `app/main.py`
   - `app/core/config.py`
   - `app/core/database.py`
   - `app/core/security.py`
   - `app/api/v1/router.py`
   - `app/models/`
   - `app/schemas/`
   - `app/services/`
   - `app/jobs/`
   - `tests/`

2. Add backend dependencies:
   - FastAPI, uvicorn, pydantic, pydantic-settings
   - SQLAlchemy async, asyncpg, Alembic
   - Redis, Celery
   - httpx, orjson, python-dateutil
   - LangChain/OpenAI/Anthropic integration packages
   - pytest, pytest-asyncio, pytest-cov
   - ruff, black, mypy

3. Create `frontend/` React project structure:
   - Vite + React + TypeScript
   - Tailwind CSS
   - shared UI components
   - TanStack Query provider
   - routing shell
   - test setup with Vitest, RTL, MSW

4. Add Docker/local development:
   - `docker-compose.dev.yml`
   - PostgreSQL service
   - Redis service
   - backend service
   - frontend service

5. Add environment examples:
   - database URL
   - Redis URL
   - JWT secret
   - OpenAI/Anthropic keys
   - Telegram bot token
   - WhatsApp phone number ID and access token
   - webhook public base URL

6. Add health endpoints:
   - `GET /healthz`
   - `GET /readyz`

7. Add CI commands documentation:
   - backend lint
   - backend tests
   - frontend lint
   - frontend typecheck
   - frontend tests

## Acceptance Criteria

- [ ] Backend app starts locally.
- [ ] Frontend app starts locally.
- [ ] PostgreSQL and Redis are available in local Docker compose.
- [ ] Alembic is configured.
- [ ] Health endpoints return successful responses.
- [ ] Test runners are configured.

## Validation

```bash
cd backend
python -m pytest tests/ -v
ruff check app tests
mypy app

cd ../frontend
npm run typecheck
npm run test
npm run build
```

