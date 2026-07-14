#!/usr/bin/env python3
"""Run the Telegram bot in long-polling mode."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from app.core.config import get_settings
from app.integrations.telegram.bootstrap import ensure_models_loaded
from app.integrations.telegram.bot_service import TelegramBotService
from app.integrations.telegram.http_config import check_telegram_connectivity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

LOCK_PATH = Path(__file__).resolve().parent.parent / ".telegram_bot.pid"


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
    """Refuse to start if another run_telegram_bot.py process is already running."""
    if LOCK_PATH.exists():
        try:
            existing_pid = int(LOCK_PATH.read_text(encoding="utf-8").strip())
        except ValueError:
            existing_pid = 0
        if _pid_running(existing_pid):
            print(
                f"Another Telegram bot is already running (pid={existing_pid}).\n"
                "Stop it before starting a new instance to avoid 409 Conflict errors."
            )
            sys.exit(1)
        LOCK_PATH.unlink(missing_ok=True)

    LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")


def main() -> int:
    ensure_models_loaded()
    ensure_single_instance()

    settings = get_settings()
    if not settings.telegram_agent_bot_token:
        print("TELEGRAM_AGENT_BOT_TOKEN is not set. Add it to your .env file and retry.")
        return 1

    ok, message = asyncio.run(check_telegram_connectivity())
    if not ok:
        print(message)
        return 1
    print(message)

    try:
        # Do NOT call asyncio.run() here — it closes the loop and breaks asyncpg
        # when python-telegram-bot starts its own polling loop.
        TelegramBotService().run_polling()
    except KeyboardInterrupt:
        print("\nTelegram bot stopped.")
        return 0
    except Exception as exc:
        logging.exception("Telegram bot failed: %s: %s", type(exc).__name__, exc)
        return 1
    finally:
        LOCK_PATH.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
