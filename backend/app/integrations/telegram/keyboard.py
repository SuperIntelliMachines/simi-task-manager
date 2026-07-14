"""Telegram inline-keyboard menus for the Insurance Assistant bot.

Navigation uses InlineKeyboardMarkup only. Legacy persistent reply keyboards
(from older bot versions) are cleared via ReplyKeyboardRemove on /start.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# --- Button labels (base text; widened at render time) ---
BTN_DASHBOARD = "📊 Dashboard"
BTN_POLICIES = "📄 Policies"
BTN_RENEWALS = "🔄 Renewals"
BTN_FOLLOWUPS = "📞 Follow-ups"
BTN_HELP = "❓ Help"

BTN_KPI_SUMMARY = "📈 KPI Summary"
BTN_UPCOMING_RENEWALS = "📅 Upcoming Renewals"
BTN_PENDING_FOLLOWUPS = "📞 Pending Follow-ups"

BTN_TOTAL_POLICIES = "📋 Total Policies"
BTN_ACTIVE_POLICIES = "✅ Active Policies"
BTN_DUE_RENEWALS = "⏰ Due Renewals"
BTN_EXPIRING_POLICIES = "⚠️ Expiring Policies"
BTN_EXPIRED_POLICIES = "❌ Expired Policies"

BTN_EXPIRING_10_DAYS = "⚠️ Expiring in 10 Days"
BTN_RECENTLY_RENEWED = "✅ Recently Renewed"

BTN_PENDING_FOLLOWUPS_MENU = "📋 Pending Follow-ups"
BTN_TODAY_FOLLOWUPS = "📅 Today's Follow-ups"
BTN_CREATE_FOLLOWUP = "➕ Create Follow-up"

BTN_BACK = "⬅️ Back"

MENU_CHOOSE_LINE = "Choose an option below  :"

MAIN_MENU_PROMPT = f"🏠 Main Menu\n\n{MENU_CHOOSE_LINE}"
BACK_PROMPT = MAIN_MENU_PROMPT

MENU_OPEN_PROMPTS: dict[str, str] = {
    "dashboard": f"📊 Dashboard\n\n{MENU_CHOOSE_LINE}",
    "policies": f"📄 Policies\n\n{MENU_CHOOSE_LINE}",
    "renewals": f"🔄 Renewals\n\n{MENU_CHOOSE_LINE}",
    "followups": f"📞 Follow-ups\n\n{MENU_CHOOSE_LINE}",
    "help": f"❓ Help\n\n{MENU_CHOOSE_LINE}",
}

# --- Callback data ---
CB_MAIN_DASHBOARD = "dashboard"
CB_MAIN_POLICIES = "policies"
CB_MAIN_RENEWALS = "renewals"
CB_MAIN_FOLLOWUPS = "followups"
CB_MAIN_HELP = "help"
CB_MENU_MAIN = "menu:main"

CB_ACTION_KPI = "action:dashboard.kpi"
CB_ACTION_UPCOMING_RENEWALS = "action:dashboard.upcoming_renewals"
CB_ACTION_PENDING_FOLLOWUPS = "action:dashboard.pending_followups"

CB_ACTION_TOTAL_POLICIES = "action:policies.total"
CB_ACTION_ACTIVE_POLICIES = "action:policies.active"
CB_ACTION_POLICIES_DUE = "action:policies.due_renewals"
CB_ACTION_EXPIRING_POLICIES = "action:policies.expiring"
CB_ACTION_EXPIRED_POLICIES = "action:policies.expired"

CB_ACTION_RENEWALS_DUE = "action:renewals.due_renewals"
CB_ACTION_EXPIRING_10 = "action:renewals.expiring_10_days"
CB_ACTION_RECENTLY_RENEWED = "action:renewals.recently_renewed"

CB_ACTION_FOLLOWUPS_PENDING = "action:followups.pending"
CB_ACTION_FOLLOWUPS_TODAY = "action:followups.today"
CB_ACTION_FOLLOWUPS_CREATE = "action:followups.create"

# Legacy inline callbacks (older messages)
CB_LEGACY_DASHBOARD = "action:dashboard"
CB_LEGACY_POLICIES = "action:policies"
CB_LEGACY_RENEWALS = "action:renewals"
CB_LEGACY_FOLLOWUPS = "action:followups"
CB_LEGACY_HELP = "action:help"


class MenuKind(str, Enum):
    MAIN = "main"
    DASHBOARD = "dashboard"
    POLICIES = "policies"
    RENEWALS = "renewals"
    FOLLOWUPS = "followups"


@dataclass(frozen=True)
class MenuOpen:
    menu: MenuKind
    prompt: str


@dataclass(frozen=True)
class MenuBack:
    prompt: str = BACK_PROMPT


@dataclass(frozen=True)
class MenuExecute:
    action: str
    menu: MenuKind


MenuInteraction = MenuOpen | MenuBack | MenuExecute


class MenuContextStore:
    """Tracks the active inline menu per Telegram user."""

    def __init__(self) -> None:
        self._menus: dict[str, MenuKind] = {}

    def get(self, external_user_id: str) -> MenuKind:
        return self._menus.get(external_user_id, MenuKind.MAIN)

    def set(self, external_user_id: str, menu: MenuKind) -> None:
        self._menus[external_user_id] = menu
        logger.info("Telegram menu context user=%s menu=%s", external_user_id, menu.value)

    def clear(self, external_user_id: str) -> None:
        if external_user_id in self._menus:
            logger.info("Telegram menu context cleared user=%s", external_user_id)
            del self._menus[external_user_id]


menu_context_store = MenuContextStore()

_MENU_OPEN_CALLBACKS: dict[str, MenuKind] = {
    CB_MAIN_DASHBOARD: MenuKind.DASHBOARD,
    CB_MAIN_POLICIES: MenuKind.POLICIES,
    CB_MAIN_RENEWALS: MenuKind.RENEWALS,
    CB_MAIN_FOLLOWUPS: MenuKind.FOLLOWUPS,
    CB_LEGACY_DASHBOARD: MenuKind.DASHBOARD,
    CB_LEGACY_POLICIES: MenuKind.POLICIES,
    CB_LEGACY_RENEWALS: MenuKind.RENEWALS,
    CB_LEGACY_FOLLOWUPS: MenuKind.FOLLOWUPS,
}

_ACTION_CALLBACKS: dict[str, tuple[str, MenuKind]] = {
    CB_MAIN_HELP: ("main.help", MenuKind.MAIN),
    CB_LEGACY_HELP: ("main.help", MenuKind.MAIN),
    CB_ACTION_KPI: ("dashboard.kpi", MenuKind.DASHBOARD),
    CB_ACTION_UPCOMING_RENEWALS: ("dashboard.upcoming_renewals", MenuKind.DASHBOARD),
    CB_ACTION_PENDING_FOLLOWUPS: ("dashboard.pending_followups", MenuKind.DASHBOARD),
    CB_ACTION_TOTAL_POLICIES: ("policies.total", MenuKind.POLICIES),
    CB_ACTION_ACTIVE_POLICIES: ("policies.active", MenuKind.POLICIES),
    CB_ACTION_POLICIES_DUE: ("policies.due_renewals", MenuKind.POLICIES),
    CB_ACTION_EXPIRING_POLICIES: ("policies.expiring", MenuKind.POLICIES),
    CB_ACTION_EXPIRED_POLICIES: ("policies.expired", MenuKind.POLICIES),
    CB_ACTION_RENEWALS_DUE: ("renewals.due_renewals", MenuKind.RENEWALS),
    CB_ACTION_EXPIRING_10: ("renewals.expiring_10_days", MenuKind.RENEWALS),
    CB_ACTION_RECENTLY_RENEWED: ("renewals.recently_renewed", MenuKind.RENEWALS),
    CB_ACTION_FOLLOWUPS_PENDING: ("followups.pending", MenuKind.FOLLOWUPS),
    CB_ACTION_FOLLOWUPS_TODAY: ("followups.today", MenuKind.FOLLOWUPS),
    CB_ACTION_FOLLOWUPS_CREATE: ("followups.create", MenuKind.FOLLOWUPS),
}


def format_menu_prompt(title: str) -> str:
    """Build consistent menu title text shown above inline buttons."""
    return f"{title}\n\n{MENU_CHOOSE_LINE}"


def widen_label(label: str) -> str:
    """Add visual spacing after emoji for clearer, wider button labels."""
    emoji, separator, text = label.partition(" ")
    if separator and text:
        return f"{emoji}  {text}"
    return label


def _pad_label(label: str, width: int) -> str:
    widened = widen_label(label)
    if len(widened) >= width:
        return widened
    return widened + " " * (width - len(widened))


def _button(label: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(widen_label(label), callback_data=callback_data)


def _button_row(label: str, callback_data: str) -> list[InlineKeyboardButton]:
    return [_button(label, callback_data)]


def _button_pair(
    left_label: str,
    left_callback: str,
    right_label: str,
    right_callback: str,
) -> list[InlineKeyboardButton]:
    left = widen_label(left_label)
    right = widen_label(right_label)
    width = max(len(left), len(right))
    return [
        InlineKeyboardButton(_pad_label(left_label, width), callback_data=left_callback),
        InlineKeyboardButton(_pad_label(right_label, width), callback_data=right_callback),
    ]


def parse_callback_data(data: str | None) -> MenuInteraction | None:
    """Map inline button callback_data to a menu interaction."""
    if not data:
        return None

    callback = data.strip()
    if callback in {CB_MENU_MAIN, "back"}:
        return MenuBack()

    menu = _MENU_OPEN_CALLBACKS.get(callback)
    if menu is not None:
        return MenuOpen(menu=menu, prompt=MENU_OPEN_PROMPTS[menu.value])

    action_entry = _ACTION_CALLBACKS.get(callback)
    if action_entry is not None:
        action, parent_menu = action_entry
        return MenuExecute(action=action, menu=parent_menu)

    return None


def inline_keyboard(menu: MenuKind = MenuKind.MAIN) -> InlineKeyboardMarkup:
    """Build compact inline keyboard attached below bot messages."""
    if menu == MenuKind.DASHBOARD:
        rows = [
            _button_pair(BTN_KPI_SUMMARY, CB_ACTION_KPI, BTN_UPCOMING_RENEWALS, CB_ACTION_UPCOMING_RENEWALS),
            _button_row(BTN_PENDING_FOLLOWUPS, CB_ACTION_PENDING_FOLLOWUPS),
            _button_row(BTN_BACK, CB_MENU_MAIN),
        ]
    elif menu == MenuKind.POLICIES:
        rows = [
            _button_pair(BTN_TOTAL_POLICIES, CB_ACTION_TOTAL_POLICIES, BTN_ACTIVE_POLICIES, CB_ACTION_ACTIVE_POLICIES),
            _button_pair(BTN_DUE_RENEWALS, CB_ACTION_POLICIES_DUE, BTN_EXPIRING_POLICIES, CB_ACTION_EXPIRING_POLICIES),
            _button_row(BTN_EXPIRED_POLICIES, CB_ACTION_EXPIRED_POLICIES),
            _button_row(BTN_BACK, CB_MENU_MAIN),
        ]
    elif menu == MenuKind.RENEWALS:
        rows = [
            _button_pair(BTN_DUE_RENEWALS, CB_ACTION_RENEWALS_DUE, BTN_EXPIRING_10_DAYS, CB_ACTION_EXPIRING_10),
            _button_row(BTN_RECENTLY_RENEWED, CB_ACTION_RECENTLY_RENEWED),
            _button_row(BTN_BACK, CB_MENU_MAIN),
        ]
    elif menu == MenuKind.FOLLOWUPS:
        rows = [
            _button_pair(
                BTN_PENDING_FOLLOWUPS_MENU,
                CB_ACTION_FOLLOWUPS_PENDING,
                BTN_TODAY_FOLLOWUPS,
                CB_ACTION_FOLLOWUPS_TODAY,
            ),
            _button_row(BTN_CREATE_FOLLOWUP, CB_ACTION_FOLLOWUPS_CREATE),
            _button_row(BTN_BACK, CB_MENU_MAIN),
        ]
    else:
        rows = [
            _button_pair(BTN_DASHBOARD, CB_MAIN_DASHBOARD, BTN_POLICIES, CB_MAIN_POLICIES),
            _button_pair(BTN_RENEWALS, CB_MAIN_RENEWALS, BTN_FOLLOWUPS, CB_MAIN_FOLLOWUPS),
            _button_row(BTN_HELP, CB_MAIN_HELP),
        ]

    return InlineKeyboardMarkup(rows)


def inline_keyboard_dict(menu: MenuKind = MenuKind.MAIN) -> dict:
    """JSON-serializable inline markup for webhook / HTTP API calls."""
    return inline_keyboard(menu).to_dict()


def empty_inline_keyboard_dict() -> dict:
    """Remove inline buttons when editing an existing Telegram message."""
    return {"inline_keyboard": []}


def remove_reply_keyboard_dict() -> dict:
    """Dismiss a stale persistent reply keyboard still shown in the Telegram client."""
    return {"remove_keyboard": True}


class _TelegramMessageSender(Protocol):
    async def send_message(self, chat_id: int, text: str, *, reply_markup: Any = None) -> Any: ...

    async def delete_message(self, chat_id: int, message_id: int) -> Any: ...


async def dismiss_legacy_reply_keyboard(bot: _TelegramMessageSender, chat_id: int) -> None:
    """Remove old ReplyKeyboardMarkup from the client (not used for navigation)."""
    from telegram import ReplyKeyboardRemove

    try:
        sent = await bot.send_message(
            chat_id=chat_id,
            text=".",
            reply_markup=ReplyKeyboardRemove(),
        )
        message_id = getattr(sent, "message_id", None)
        if message_id is not None:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        logger.exception("Failed to dismiss legacy reply keyboard chat=%s", chat_id)


async def dismiss_legacy_reply_keyboard_via_api(client: Any, chat_id: str | int) -> None:
    """Webhook helper: dismiss stale reply keyboard using HTTP API client."""
    try:
        data = await client.send_message(chat_id, ".", reply_markup=remove_reply_keyboard_dict())
        result = data.get("result") or {}
        message_id = result.get("message_id")
        if message_id is not None:
            await client.delete_message(chat_id, message_id)
    except Exception:
        logger.exception("Failed to dismiss legacy reply keyboard chat=%s", chat_id)


def normalize_button_text(text: str) -> str:
    """Collapse padded label text for comparisons and tests."""
    return " ".join(text.split())


def map_keyboard_label(text: str) -> str | None:
    """Legacy hook used by parse_message; menus use inline callbacks only."""
    return None
