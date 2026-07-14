from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Task Manager"
    app_version: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    app_env: str = Field(
        default="development",
        description="Runtime environment: development | staging | production",
    )
    frontend_base_url: str = Field(
        default="http://localhost:5173",
        description="Frontend origin used when building password-reset links.",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/task_manager"
    )
    database_admin_url: str = Field(
        default="",
        description="Optional superuser/owner URL for Alembic DDL migrations.",
    )
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    password_reset_expire_minutes: int = 30
    min_password_length: int = 8
    max_failed_login_attempts: int = 5
    account_lockout_minutes: int = 15
    login_rate_limit_per_minute: int = 20

    openai_api_key: str = ""
    anthropic_api_key: str = ""

    telegram_agent_bot_token: str = ""
    telegram_customer_bot_token: str = ""
    telegram_default_organization_id: int = 0
    telegram_webhook_secret: str = ""
    telegram_proxy_url: str = ""
    telegram_api_base_url: str = "https://api.telegram.org"
    telegram_connect_timeout: float = 30.0
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_api_version: str = "v22.0"
    whatsapp_template_name: str = "welcome"
    whatsapp_template_language: str = "en_US"
    use_whatsapp_session_text: bool = False
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    webhook_public_base_url: str = ""
    insurance_premium_payment_link: str = "https://ebiz.licindia.in/spy-LIC"

    enable_dev_reminder_scheduler: bool = False
    scheduler_secret: str = ""
    default_reminder_time: str = "09:00"
    default_reminder_timezone: str = "Asia/Kolkata"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = ""

    # External Gyantr AI Claims module (read-only integration)
    claims_base_url: str = Field(
        default="",
        description="Base URL for the external Gyantr AI Claims API (no trailing slash).",
    )
    claims_username: str = Field(default="", description="Claims service username for JWT auth.")
    claims_password: str = Field(default="", description="Claims service password for JWT auth.")
    claims_timeout: float = Field(
        default=30.0,
        description="HTTP timeout in seconds for Claims API requests.",
    )
    claims_auth_path: str = Field(
        default="/auth/login",
        description=(
            "Path (relative to CLAIMS_BASE_URL) for Gyantr login. "
            "Default /auth/login → POST {CLAIMS_BASE_URL}/auth/login."
        ),
    )
    claims_api_prefix: str = Field(
        default="/crm",
        description=(
            "Path prefix appended after CLAIMS_BASE_URL for Claims resources. "
            "Gyantr Service Cases live under /crm (e.g. base .../api/v1 + /crm + /service-cases)."
        ),
    )
    claims_tenant_slug: str = Field(
        default="",
        description="Gyantr tenant_slug required by POST /auth/login (unless tenant_id is set).",
    )
    claims_tenant_id: str = Field(
        default="",
        description="Optional Gyantr tenant UUID for POST /auth/login (alternative to tenant_slug).",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def is_development(self) -> bool:
        return not self.is_production

    @property
    def claims_configured(self) -> bool:
        has_tenant = bool(self.claims_tenant_slug.strip() or self.claims_tenant_id.strip())
        return bool(
            self.claims_base_url.strip()
            and self.claims_username.strip()
            and self.claims_password
            and has_tenant
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
