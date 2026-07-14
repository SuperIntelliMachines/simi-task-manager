import pytest

from app.integrations.telegram.parsers import (
    DemoLogCommand,
    FollowupLogCommand,
    GreetingCommand,
    PolicyCreateCommand,
    PolicyQueryCommand,
    PolicyRenewCommand,
    RenewalsQueryCommand,
    parse_greeting,
    parse_message,
    parse_policy_query_intent,
    strip_nl_filler,
)


def test_parse_start_command():
    assert parse_message("/start") == "/start"


def test_parse_demo_log_command():
    parsed = parse_message("Log demo for Sanju today and remind me in 3 days")
    assert isinstance(parsed, DemoLogCommand)
    assert parsed.customer_name == "Sanju"
    assert parsed.followup_days == 3


def test_parse_policy_create_command():
    parsed = parse_message("Create a Health policy for Ravi expiring on June 25")
    assert isinstance(parsed, PolicyCreateCommand)
    assert parsed.customer_name == "Ravi"
    assert parsed.policy_type == "Health"
    assert parsed.expiry_date.month == 6
    assert parsed.expiry_date.day == 25


def test_parse_policy_create_without_on():
    parsed = parse_message("Create a Health policy for Ravi expiring June 25")
    assert isinstance(parsed, PolicyCreateCommand)
    assert parsed.customer_name == "Ravi"
    assert parsed.policy_type == "Health"


def test_parse_car_policy_maps_to_motor():
    parsed = parse_message("Create a Car policy for Kumar expiring July 10")
    assert isinstance(parsed, PolicyCreateCommand)
    assert parsed.customer_name == "Kumar"
    assert parsed.policy_type == "Motor"
    assert parsed.expiry_date.month == 7
    assert parsed.expiry_date.day == 10
    assert parsed.reminder_channel is None


@pytest.mark.parametrize(
    ("text", "customer", "policy_type", "month", "day", "reminder"),
    [
        (
            "Create a Motor policy for Kishan expiring July 26 and remind him on WhatsApp",
            "Kishan",
            "Motor",
            7,
            26,
            "WhatsApp",
        ),
        (
            "Create a Health policy for Ravi expiring June 25 and remind him on Telegram",
            "Ravi",
            "Health",
            6,
            25,
            "Telegram",
        ),
        (
            "Create a Life policy for Kumar expiring August 10 and send reminder",
            "Kumar",
            "Life",
            8,
            10,
            "General",
        ),
        (
            "Create a Health policy for Anu expiring September 5 and notify customer",
            "Anu",
            "Health",
            9,
            5,
            "General",
        ),
        (
            "Create a Motor policy for Kishan expiring July 26",
            "Kishan",
            "Motor",
            7,
            26,
            None,
        ),
    ],
)
def test_parse_policy_create_with_optional_reminder(text, customer, policy_type, month, day, reminder):
    parsed = parse_message(text)
    assert isinstance(parsed, PolicyCreateCommand)
    assert parsed.customer_name == customer
    assert parsed.policy_type == policy_type
    assert parsed.expiry_date.month == month
    assert parsed.expiry_date.day == day
    assert parsed.reminder_channel == reminder


def test_parse_log_followup_command():
    parsed = parse_message("Log a follow-up for Priya in 3 days")
    assert isinstance(parsed, FollowupLogCommand)
    assert parsed.customer_name == "Priya"
    assert parsed.followup_days == 3


def test_parse_policy_renew_commands():
    cases = [
        ("Mark Kumar's policy renewed", "Kumar"),
        ("Mark Ian's policy renewed", "Ian"),
        ("Renew Ravi's policy", "Ravi"),
        ("Renew Ian policy", "Ian"),
        ("Renew Kumar policy", "Kumar"),
        ("Policy renewed for Ravi", "Ravi"),
        ("Mark policy renewed for Sanju", "Sanju"),
        ("Mark Ian\u2019s policy renewed", "Ian"),
        ("Mark Ian policy renewed", "Ian"),
        ("Renew policy for Ian", "Ian"),
    ]
    for text, expected_name in cases:
        parsed = parse_message(text)
        assert isinstance(parsed, PolicyRenewCommand), text
        assert parsed.customer_name == expected_name, text


def test_parse_auto_policy_type_maps_to_motor():
    parsed = parse_message("Create a Auto policy for Ramesh expiring on July 10")
    assert isinstance(parsed, PolicyCreateCommand)
    assert parsed.policy_type == "Motor"


def test_parse_renewals_query():
    parsed = parse_message("Show policies expiring in next 10 days")
    assert isinstance(parsed, RenewalsQueryCommand)
    assert parsed.days == 10


def test_parse_pending_followups_query():
    parsed = parse_message("Show pending follow-ups")
    assert isinstance(parsed, PolicyQueryCommand)
    assert parsed.action == "followups.pending"
    assert parsed.intent == "show_pending_followups"


@pytest.mark.parametrize(
    ("text", "action", "intent"),
    [
        ("show policies", "policies.total", "show_policies"),
        ("show all policies", "policies.total", "show_all_policies"),
        ("policy summary", "policies.summary", "policy_summary"),
        ("show policy summary", "policies.summary", "show_policy_summary"),
        ("show active policies", "policies.active", "show_active_policies"),
        ("active policies", "policies.active", "active_policies"),
        ("list active policies", "policies.active", "list_active_policies"),
        ("show expiring policies", "policies.expiring", "show_expiring_policies"),
        ("expiring policies", "policies.expiring", "expiring_policies"),
        ("policies expiring soon", "policies.expiring", "policies_expiring_soon"),
        ("show expired policies", "policies.expired", "show_expired_policies"),
        ("expired policies", "policies.expired", "expired_policies"),
        ("show due renewals", "policies.due_renewals", "show_due_renewals"),
        ("due renewals", "policies.due_renewals", "due_renewals"),
        ("show followups", "/followups", None),
        ("pending followups", "followups.pending", "pending_followups"),
        ("pending follow-ups", "followups.pending", "pending_followups"),
    ],
)
def test_parse_policy_query_intents(text, action, intent):
    parsed = parse_message(text)
    if intent is None:
        assert parsed == action
        return
    assert isinstance(parsed, PolicyQueryCommand)
    assert parsed.action == action
    assert parsed.intent == intent


@pytest.mark.parametrize(
    ("text", "action"),
    [
        ("please show active policies", "policies.active"),
        ("can you show active policies", "policies.active"),
        ("show me active policies", "policies.active"),
        ("Please Show Expiring Policies", "policies.expiring"),
        ("could you list active policies", "policies.active"),
    ],
)
def test_parse_policy_query_with_filler_words(text, action):
    parsed = parse_policy_query_intent(text)
    assert isinstance(parsed, PolicyQueryCommand)
    assert parsed.action == action


def test_strip_nl_filler():
    assert strip_nl_filler("please show active policies") == "show active policies"
    assert strip_nl_filler("can you show active policies") == "show active policies"
    assert strip_nl_filler("show me active policies") == "active policies"


@pytest.mark.parametrize(
    ("text", "command"),
    [
        ("dashboard", "/dashboard"),
        ("Dashboard", "/dashboard"),
        ("show dashboard", "/dashboard"),
        ("SHOW DASHBOARD", "/dashboard"),
        ("insurance dashboard", "/dashboard"),
        ("show insurance dashboard", "/dashboard"),
        ("dashboard.", "/dashboard"),
        ("policies", "/policies"),
        ("  policies  ", "/policies"),
        ("renewals", "/renewals"),
        ("show renewals", "/renewals"),
        ("upcoming renewals", "/renewals"),
        ("Upcoming Renewals!", "/renewals"),
        ("followups", "/followups"),
        ("follow-ups", "/followups"),
        ("show followups", "/followups"),
        ("show follow-ups", "/followups"),
    ],
)
def test_parse_navigation_intents(text, command):
    assert parse_message(text) == command


def test_renewals_with_days_takes_priority_over_navigation_intent():
    parsed = parse_message("Show policies expiring in next 10 days")
    assert isinstance(parsed, RenewalsQueryCommand)
    assert parsed.days == 10


@pytest.mark.parametrize(
    ("text", "expected_days"),
    [
        ("show expiring policies in next 5 days", 5),
        ("show expiring policies in next 10 days", 10),
        ("show expiring policies in next 15 days", 15),
        ("show expiring policies in next 30 days", 30),
        ("Show Expiring Policies In Next 5 Days", 5),
        ("policies expiring in 5 days", 5),
        ("expiring policies next 10 days", 10),
        ("please show expiring policies in next 7 days", 7),
        ("show policies expiring in next 12 days", 12),
    ],
)
def test_parse_expiring_policies_days_queries(text, expected_days):
    parsed = parse_message(text)
    assert isinstance(parsed, RenewalsQueryCommand)
    assert parsed.days == expected_days


def test_show_expiring_policies_without_days_uses_static_intent():
    parsed = parse_message("show expiring policies")
    assert isinstance(parsed, PolicyQueryCommand)
    assert parsed.action == "policies.expiring"


def test_parse_unknown_message_returns_none():
    assert parse_message("totally unknown request xyz") is None


@pytest.mark.parametrize(
    ("text", "word"),
    [
        ("hi", "hi"),
        ("Hi", "hi"),
        ("HI", "hi"),
        ("hello", "hello"),
        ("Hello", "hello"),
        ("hey", "hey"),
        ("Hey", "hey"),
        ("hey there", "hey"),
        ("HI!", "hi"),
    ],
)
def test_parse_greeting(text, word):
    parsed = parse_message(text)
    assert isinstance(parsed, GreetingCommand)
    assert parsed.word == word
    assert parse_greeting(text) == parsed
