import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.seeds.rbac_seed import seed_rbac

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task: asyncio.Task[None] | None = None
    stop_event: asyncio.Event | None = None

    try:
        async with AsyncSessionLocal() as session:
            await seed_rbac(session)
    except Exception as exc:
        logger.warning("RBAC seed skipped during startup: %s", exc)

    # Note: there is no ENABLE_INPROCESS_SCHEDULER setting in this codebase.
    print(
        f"[ReminderScheduler] ENABLE_DEV_REMINDER_SCHEDULER={settings.enable_dev_reminder_scheduler}",
        flush=True,
    )
    logger.info(
        "[ReminderScheduler] Runtime config ENABLE_DEV_REMINDER_SCHEDULER=%s "
        "(ENABLE_INPROCESS_SCHEDULER is not used by this app)",
        settings.enable_dev_reminder_scheduler,
    )

    if settings.enable_dev_reminder_scheduler:
        from app.jobs.dev_reminder_scheduler import start_dev_reminder_scheduler

        print("[ReminderScheduler] ENABLED", flush=True)
        logger.info("[ReminderScheduler] Enabled via ENABLE_DEV_REMINDER_SCHEDULER=true")
        scheduler_task, stop_event = start_dev_reminder_scheduler()
        print("[ReminderScheduler] Scheduler task created", flush=True)
    else:
        logger.info("[ReminderScheduler] Disabled (ENABLE_DEV_REMINDER_SCHEDULER=false)")

    yield

    if stop_event is not None and scheduler_task is not None:
        stop_event.set()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# Allow the frontend dev server (Vite) to call the API during local development.
_dev_allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_dev_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

_uploads_dir = Path(__file__).resolve().parents[2] / "uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root to the interactive API docs."""
    return RedirectResponse(url="/docs")


# Convenience root-level health endpoints to support external health checks
@app.get("/health", include_in_schema=False)
async def health_root():
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
async def ready_root():
    # Call into the same logic as the API-ready endpoint by delegating to it.
    # Import locally to avoid circular imports at module load time.
    from app.api.v1.endpoints.health import readyz

    return await readyz()
