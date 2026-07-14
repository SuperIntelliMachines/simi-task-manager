"""Natural-language parsers for Telegram insurance commands."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from dateutil import parser as date_parser
from dateutil.parser import ParserError

from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive

logger = logging.getLogger(__name__)

DEMO_LOG_PATTERN = re.compile(
    r"^log\s+(?:a\s+)?demo\s+for\s+(?P<name>.+?)\s+today\s+and\s+remind\s+me\s+in\s+(?P<days>\d+)\s+days?\s*$",
    re.IGNORECASE,
)
LOG_FOLLOWUP_PATTERN = re.compile(
    r"^log\s+(?:a\s+)?follow[\-\s]?up\s+for\s+(?P<name>.+?)\s+in\s+(?P<days>\d+)\s+days?\s*$",
    re.IGNORECASE,
)
POLICY_CREATE_CORE_PATTERN = re.compile(
    r"^create\s+(?:a\s+)?(?P<policy_type>health|life|motor|auto|car|general)\s+policy\s+for\s+(?P<name>.+?)\s+expiring(?:\s+on)?\s+(?P<date>.+?)\s*$",
    re.IGNORECASE,
)
POLICY_CREATE_REMINDER_SUFFIX = re.compile(
    r"\s+and\s+(?P<reminder>(?:remind\b|send\s+reminder|notify\s+customer).*)$",
    re.IGNORECASE,
)
POLICY_RENEW_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^mark\s+policy\s+renewed\s+for\s+(?P<name>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^policy\s+renewed\s+for\s+(?P<name>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^renew\s+policy\s+for\s+(?P<name>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^mark\s+(?P<name>.+?)'?s?\s+policy\s+renewed\s*$", re.IGNORECASE),
    re.compile(r"^renew\s+(?P<name>.+?)'?s?\s+policy\s*$", re.IGNORECASE),
)
RENEWALS_QUERY_PATTERN = re.compile(
    r"^show\s+policies\s+expiring\s+in\s+(?:next\s+)?(?P<days>\d+)\s+days?\s*$",
    re.IGNORECASE,
)
EXPIRING_POLICIES_DAYS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^show\s+expiring\s+policies(?:\s+in)?(?:\s+(?:the\s+)?next)?(?:\s+(?P<days>\d+))?\s+days?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^show\s+policies\s+expiring\s+in(?:\s+(?:the\s+)?next)?(?:\s+(?P<days>\d+))?\s+days?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^policies\s+expiring\s+in\s+(?P<days>\d+)\s+days?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^expiring\s+policies(?:\s+(?:in\s+)?(?:the\s+)?next)?\s+(?P<days>\d+)\s+days?\s*$",
        re.IGNORECASE,
    ),
)
DEFAULT_EXPIRING_QUERY_DAYS = 30
GREETING_PATTERN = re.compile(r"^(?P<greeting>hello|hey|hi)\b", re.IGNORECASE)

GREETING_WORDS = frozenset({"hi", "hello", "hey"})

_NAVIGATION_PHRASE_TO_COMMAND: dict[str, str] = {
    "dashboard": "/dashboard",
    "show dashboard": "/dashboard",
    "insurance dashboard": "/dashboard",
    "show insurance dashboard": "/dashboard",
    "policies": "/policies",
    "renewals": "/renewals",
    "show renewals": "/renewals",
    "upcoming renewals": "/renewals",
    "upcoming renewal": "/renewals",
    "show upcoming renewals": "/renewals",
    "show upcoming renewal": "/renewals",
    "followups": "/followups",
    "follow ups": "/followups",
    "show followups": "/followups",
    "show follow ups": "/followups",
    "show follow-ups": "/followups",
}

_NL_FILLER_PREFIXES: tuple[str, ...] = (
    r"please\s+",
    r"kindly\s+",
    r"can you\s+",
    r"could you\s+",
    r"would you\s+",
    r"show me\s+",
    r"tell me\s+",
    r"give me\s+",
    r"i want to\s+",
    r"i need to\s+",
    r"list\s+",
)

# Longer phrases first so matching prefers the most specific intent.
_POLICY_QUERY_PHRASES: tuple[tuple[str, str, str], ...] = (
    ("show policy summary", "policies.summary", "show_policy_summary"),
    ("show all policies", "policies.total", "show_all_policies"),
    ("show active policies", "policies.active", "show_active_policies"),
    ("list active policies", "policies.active", "list_active_policies"),
    ("show expiring policies", "policies.expiring", "show_expiring_policies"),
    ("policies expiring soon", "policies.expiring", "policies_expiring_soon"),
    ("show lapsed policies", "policies.expired", "show_lapsed_policies"),
    ("show due renewals", "policies.due_renewals", "show_due_renewals"),
    ("show pending follow ups", "followups.pending", "show_pending_followups"),
    ("show pending followups", "followups.pending", "show_pending_followups"),
    ("show pending follow-ups", "followups.pending", "show_pending_followups"),
    ("policy summary", "policies.summary", "policy_summary"),
    ("show policies", "policies.total", "show_policies"),
    ("active policies", "policies.active", "active_policies"),
    ("expiring policies", "policies.expiring", "expiring_policies"),
    ("lapsed policies", "policies.expired", "lapsed_policies"),
    ("due renewals", "policies.due_renewals", "due_renewals"),
    ("pending follow ups", "followups.pending", "pending_followups"),
    ("pending followups", "followups.pending", "pending_followups"),
    ("pending follow-ups", "followups.pending", "pending_followups"),
)


@dataclass(frozen=True)
class GreetingCommand:
    word: str


@dataclass(frozen=True)
class DemoLogCommand:
    customer_name: str
    followup_days: int


@dataclass(frozen=True)
class FollowupLogCommand:
    customer_name: str
    followup_days: int
    notes: str | None = None


@dataclass(frozen=True)
class PolicyCreateCommand:
    customer_name: str
    policy_type: str
    expiry_date: datetime
    reminder_channel: str | None = None


@dataclass(frozen=True)
class PolicyRenewCommand:
    customer_name: str


@dataclass(frozen=True)
class RenewalsQueryCommand:
    days: int


@dataclass(frozen=True)
class PolicyQueryCommand:
    """Natural-language policy / renewal / follow-up list query."""

    action: str
    intent: str


ParsedCommand = (
    DemoLogCommand
    | FollowupLogCommand
    | PolicyCreateCommand
    | PolicyRenewCommand
    | RenewalsQueryCommand
    | PolicyQueryCommand
    | GreetingCommand
    | str
    | None
)


def parse_expiry_date(raw: str) -> datetime:
    """Parse dates like 'June 25' or '25-Jun-2026'."""
    now = utcnow_naive()
    parsed = date_parser.parse(raw.strip(), default=now.replace(month=1, day=1))
    parsed = parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    if parsed.year == now.year and parsed.date() < now.date():
        parsed = parsed.replace(year=now.year + 1)
    end_of_day = parsed.replace(hour=23, minute=59, second=59, microsecond=0)
    return normalize_to_utc_naive(end_of_day)


def parse_renewal_date(text: str) -> datetime | None:
    """Parse a user-supplied renewal expiry date; return None if invalid."""
    stripped = normalize_user_text(text)
    if not stripped or stripped.startswith("/"):
        return None
    try:
        return parse_expiry_date(stripped)
    except (ValueError, OverflowError, TypeError, ParserError):
        return None


def normalize_policy_type(raw: str) -> str:
    value = raw.strip().lower()
    if value in {"auto", "car"}:
        value = "motor"
    return value.capitalize()


def normalize_intent_text(text: str) -> str:
    """Lowercase, trim, collapse whitespace, and strip punctuation for intent matching."""
    value = (text or "").strip().lower()
    value = value.replace("-", " ")
    value = re.sub(r"[^\w\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def log_detected_intent(parsed: ParsedCommand, raw_text: str) -> None:
    """Log the detected intent and extracted entities."""
    if parsed is None:
        return
    if isinstance(parsed, str):
        if parsed.startswith("/"):
            logger.info("Telegram intent detected: %s (input=%r)", parsed.lstrip("/"), raw_text)
        return
    if isinstance(parsed, GreetingCommand):
        logger.info("Telegram intent detected: greeting word=%s (input=%r)", parsed.word, raw_text)
    elif isinstance(parsed, PolicyCreateCommand):
        logger.info(
            "Telegram intent detected: create_policy customer=%s policy_type=%s expiry=%s "
            "reminder_channel=%s (input=%r)",
            parsed.customer_name,
            parsed.policy_type,
            parsed.expiry_date.date().isoformat(),
            parsed.reminder_channel,
            raw_text,
        )
    elif isinstance(parsed, FollowupLogCommand):
        logger.info(
            "Telegram intent detected: log_followup customer=%s followup_days=%s notes=%r (input=%r)",
            parsed.customer_name,
            parsed.followup_days,
            parsed.notes,
            raw_text,
        )
    elif isinstance(parsed, DemoLogCommand):
        logger.info(
            "Telegram intent detected: log_demo customer=%s followup_days=%s (input=%r)",
            parsed.customer_name,
            parsed.followup_days,
            raw_text,
        )
    elif isinstance(parsed, PolicyRenewCommand):
        logger.info(
            "Telegram intent detected: renew_policy customer=%s (input=%r)",
            parsed.customer_name,
            raw_text,
        )
    elif isinstance(parsed, RenewalsQueryCommand):
        logger.info(
            "Telegram intent detected: renewals_query days=%s (input=%r)",
            parsed.days,
            raw_text,
        )
    elif isinstance(parsed, PolicyQueryCommand):
        logger.info(
            "Telegram intent detected: %s action=%s (input=%r)",
            parsed.intent,
            parsed.action,
            raw_text,
        )


def strip_nl_filler(normalized: str) -> str:
    """Remove polite/filler prefixes so phrases like 'please show active policies' match."""
    value = normalized.strip()
    while True:
        previous = value
        for pattern in _NL_FILLER_PREFIXES:
            value = re.sub(f"^{pattern}", "", value, flags=re.IGNORECASE)
        if value == previous:
            break
    return value.strip()


def parse_policy_query_intent(text: str) -> PolicyQueryCommand | None:
    """Map natural-language policy list queries to menu actions."""
    normalized = normalize_intent_text(text)
    if not normalized:
        return None

    candidates = (normalized, strip_nl_filler(normalized))
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        for phrase, action, intent in _POLICY_QUERY_PHRASES:
            if candidate == phrase:
                parsed = PolicyQueryCommand(action=action, intent=intent)
                logger.info(
                    "Telegram intent detected: %s action=%s (input=%r normalized=%r)",
                    intent,
                    action,
                    text,
                    candidate,
                )
                return parsed

    return None


def parse_navigation_intent(text: str) -> str | None:
    """Map natural-language navigation phrases to slash commands."""
    normalized = normalize_intent_text(text)
    if not normalized:
        return None

    command = _NAVIGATION_PHRASE_TO_COMMAND.get(normalized)
    if command is None:
        logger.info(
            "Telegram navigation intent not matched input=%r normalized=%r",
            text,
            normalized,
        )
        return None

    intent = command.lstrip("/")
    logger.info(
        "Telegram intent detected: %s (input=%r normalized=%r)",
        intent,
        text,
        normalized,
    )
    return command


def parse_greeting(text: str) -> GreetingCommand | None:
    match = GREETING_PATTERN.match((text or "").strip())
    if not match:
        return None
    word = match.group("greeting").lower()
    if word not in GREETING_WORDS:
        return None
    return GreetingCommand(word=word)


def parse_reminder_channel(reminder_text: str) -> str | None:
    """Extract a display label for an optional reminder phrase."""
    normalized = normalize_intent_text(reminder_text)
    if not normalized:
        return None
    compact = normalized.replace(" ", "")
    if "whatsapp" in compact:
        return "WhatsApp"
    if "telegram" in normalized:
        return "Telegram"
    if "send reminder" in normalized or "notify customer" in normalized or "remind" in normalized:
        return "General"
    return None


def reminder_channel_to_preferred(channel: str | None) -> str:
    """Map parsed reminder channel to notification preferred_channel."""
    if channel == "WhatsApp":
        return "whatsapp"
    if channel == "Telegram":
        return "telegram"
    return "telegram"


def parse_policy_create(text: str) -> PolicyCreateCommand | None:
    """Parse policy creation, optionally stripping trailing reminder phrases."""
    stripped = (text or "").strip()
    if not stripped:
        return None

    policy_text = stripped
    reminder_channel: str | None = None

    reminder_suffix = POLICY_CREATE_REMINDER_SUFFIX.search(stripped)
    if reminder_suffix:
        policy_text = stripped[: reminder_suffix.start()].strip()
        reminder_channel = parse_reminder_channel(reminder_suffix.group("reminder"))

    policy_match = POLICY_CREATE_CORE_PATTERN.match(policy_text)
    if not policy_match:
        return None

    return PolicyCreateCommand(
        customer_name=policy_match.group("name").strip(),
        policy_type=normalize_policy_type(policy_match.group("policy_type")),
        expiry_date=parse_expiry_date(policy_match.group("date")),
        reminder_channel=reminder_channel,
    )


def normalize_user_text(text: str) -> str:
    """Normalize smart quotes/apostrophes from mobile keyboards."""
    value = (text or "").strip()
    return (
        value.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


def clean_customer_name(name: str) -> str:
    """Strip possessive suffix from extracted customer names (Ian’s -> Ian)."""
    cleaned = normalize_user_text(name).strip()
    return re.sub(r"'s$", "", cleaned, flags=re.IGNORECASE).strip()


def parse_expiring_policies_days_query(text: str) -> RenewalsQueryCommand | None:
    """Parse natural-language expiring-policy window queries with optional day count."""
    normalized = normalize_intent_text(text)
    if not normalized:
        return None

    candidates: list[str] = []
    for value in (normalized, strip_nl_filler(normalized)):
        if value and value not in candidates:
            candidates.append(value)

    static_expiring_phrases = {
        "show expiring policies",
        "expiring policies",
        "policies expiring soon",
    }

    for candidate in candidates:
        if candidate in static_expiring_phrases:
            continue

        for pattern in EXPIRING_POLICIES_DAYS_PATTERNS:
            match = pattern.match(candidate)
            if not match:
                continue
            days_raw = match.groupdict().get("days")
            days = int(days_raw) if days_raw else DEFAULT_EXPIRING_QUERY_DAYS
            parsed = RenewalsQueryCommand(days=days)
            logger.info(
                "Telegram expiring policies query parsed days=%s input=%r normalized=%r",
                days,
                text,
                candidate,
            )
            return parsed

    return None


def parse_policy_renew(text: str) -> PolicyRenewCommand | None:
    stripped = normalize_user_text(text)
    if not stripped:
        return None

    for pattern in POLICY_RENEW_PATTERNS:
        match = pattern.match(stripped)
        if not match:
            continue
        name = clean_customer_name(match.group("name"))
        if name:
            return PolicyRenewCommand(customer_name=name)
    return None


def parse_message(text: str) -> ParsedCommand:
    """Return a parsed command object, a slash-command name, or None."""
    from app.integrations.telegram.keyboard import map_keyboard_label

    stripped = normalize_user_text(text)
    if not stripped:
        return None

    keyboard_command = map_keyboard_label(stripped)
    if keyboard_command:
        log_detected_intent(keyboard_command, stripped)
        return keyboard_command

    greeting = parse_greeting(stripped)
    if greeting is not None:
        log_detected_intent(greeting, stripped)
        return greeting

    if stripped.startswith("/"):
        command = stripped.split()[0].split("@")[0].lower()
        log_detected_intent(command, stripped)
        return command

    demo_match = DEMO_LOG_PATTERN.match(stripped)
    if demo_match:
        parsed: ParsedCommand = DemoLogCommand(
            customer_name=demo_match.group("name").strip(),
            followup_days=int(demo_match.group("days")),
        )
        log_detected_intent(parsed, stripped)
        return parsed

    followup_match = LOG_FOLLOWUP_PATTERN.match(stripped)
    if followup_match:
        parsed = FollowupLogCommand(
            customer_name=followup_match.group("name").strip(),
            followup_days=int(followup_match.group("days")),
        )
        log_detected_intent(parsed, stripped)
        return parsed

    policy_parsed = parse_policy_create(stripped)
    if policy_parsed is not None:
        log_detected_intent(policy_parsed, stripped)
        return policy_parsed

    renew_match = parse_policy_renew(stripped)
    if renew_match is not None:
        log_detected_intent(renew_match, stripped)
        return renew_match

    expiring_days_query = parse_expiring_policies_days_query(stripped)
    if expiring_days_query is not None:
        log_detected_intent(expiring_days_query, stripped)
        return expiring_days_query

    renewals_match = RENEWALS_QUERY_PATTERN.match(stripped)
    if renewals_match:
        parsed = RenewalsQueryCommand(days=int(renewals_match.group("days")))
        log_detected_intent(parsed, stripped)
        return parsed

    policy_query = parse_policy_query_intent(stripped)
    if policy_query is not None:
        log_detected_intent(policy_query, stripped)
        return policy_query

    navigation_command = parse_navigation_intent(stripped)
    if navigation_command is not None:
        return navigation_command

    return None


def format_followup_date(days: int) -> str:
    target = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=days)
    return target.strftime("%d-%b-%Y")
