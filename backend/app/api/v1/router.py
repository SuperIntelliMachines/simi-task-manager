from fastapi import APIRouter

from app.api.v1.endpoints.agent_sessions import router as agent_sessions_router
from app.api.v1.endpoints.approval_requests import router as approval_requests_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.insurance import router as insurance_router
from app.api.v1.endpoints.message_templates import router as message_templates_router
from app.api.v1.endpoints.notification_preferences import (
	router as notification_preferences_router,
)
from app.api.v1.endpoints.channel_settings import router as channel_settings_router
from app.api.v1.endpoints.reminders import router as reminders_router
from app.api.v1.endpoints.general_reminders import router as general_reminders_router
from app.api.v1.endpoints.personal_reminders import router as personal_reminders_router
from app.api.v1.endpoints.reminder_templates import router as reminder_templates_router
from app.api.v1.endpoints.reminder_history import router as reminder_history_router
from app.api.v1.endpoints.scheduler_jobs import router as scheduler_jobs_router
from app.api.v1.endpoints.telegram_webhook import router as telegram_webhook_router
from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.whatsapp_webhook import router as whatsapp_webhook_router
from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.internal_reminders import router as internal_reminders_router
from app.api.v1.endpoints.internal_personal_reminders import (
    router as internal_personal_reminders_router,
)
from app.api.v1.endpoints.integrations_claims import router as integrations_claims_router
from app.api.v1.endpoints.notifications import router as notifications_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(approval_requests_router)
api_router.include_router(agent_sessions_router)
api_router.include_router(message_templates_router)
api_router.include_router(insurance_router)
api_router.include_router(notification_preferences_router)
api_router.include_router(notifications_router)
api_router.include_router(tasks_router)
api_router.include_router(reminders_router)
api_router.include_router(general_reminders_router)
api_router.include_router(personal_reminders_router)
api_router.include_router(reminder_templates_router)
api_router.include_router(reminder_history_router)
api_router.include_router(scheduler_jobs_router)
api_router.include_router(internal_reminders_router)
api_router.include_router(internal_personal_reminders_router)
api_router.include_router(channel_settings_router)
api_router.include_router(telegram_webhook_router)
api_router.include_router(whatsapp_webhook_router)
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(integrations_claims_router)
