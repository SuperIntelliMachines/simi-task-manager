#!/usr/bin/env python3
"""Run the customer Telegram bot in long-polling mode."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.integrations.telegram.bootstrap import ensure_models_loaded, prepare_telegram_runtime
from app.integrations.telegram.customer_onboarding import CustomerTelegramOnboardingService
from app.integrations.telegram.http_config import build_ptb_http_request, check_telegram_connectivity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

LOCK_PATH = Path(__file__).resolve().parent.parent / ".telegram_customer_bot.pid"


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import subprocess

        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in result.stdout

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def ensure_single_instance() -> None:
    """Refuse to start if another customer bot process is already running."""
    if LOCK_PATH.exists():
        try:
            existing_pid = int(LOCK_PATH.read_text(encoding="utf-8").strip())
        except ValueError:
            existing_pid = 0
        if _pid_running(existing_pid):
            print(
                f"Another customer Telegram bot is already running (pid={existing_pid}).\n"
                "Stop it before starting a new instance to avoid 409 Conflict errors."
            )
            sys.exit(1)
        LOCK_PATH.unlink(missing_ok=True)

    LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")


def build_customer_application(token: str) -> Application:
    onboarding = CustomerTelegramOnboardingService()

    async def _on_post_init(application: Application) -> None:
        await prepare_telegram_runtime()

    async def _handle_payload(update: Update) -> None:
        if update.effective_message is None:
            return
        payload = update.to_dict()
        async with AsyncSessionLocal() as session:
            reply = await onboarding.handle_payload(session=session, payload=payload)
        if reply:
            await update.effective_message.reply_text(reply)

    async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _handle_payload(update)

    async def _on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _handle_payload(update)

    application = (
        Application.builder()
        .token(token)
        .request(build_ptb_http_request())
        .post_init(_on_post_init)
        .build()
    )
    application.add_handler(CommandHandler("start", _cmd_start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_text))
    return application


def main() -> int:
    ensure_models_loaded()
    ensure_single_instance()

    settings = get_settings()
    if not settings.telegram_customer_bot_token:
        print("TELEGRAM_CUSTOMER_BOT_TOKEN is not set. Add it to your .env file and retry.")
        return 1

    ok, message = asyncio.run(check_telegram_connectivity())
    if not ok:
        print(message)
        return 1
    print(message)

    try:
        logger.info("Starting customer Telegram bot polling...")
        app = build_customer_application(settings.telegram_customer_bot_token)
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except KeyboardInterrupt:
        print("\nCustomer Telegram bot stopped.")
        return 0
    except Exception as exc:
        logger.exception("Customer Telegram bot failed: %s: %s", type(exc).__name__, exc)
        return 1
    finally:
        LOCK_PATH.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
