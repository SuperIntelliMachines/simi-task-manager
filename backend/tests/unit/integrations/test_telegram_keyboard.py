import pytest

from app.integrations.telegram.keyboard import (
    BTN_ACTIVE_POLICIES,
    BTN_BACK,
    BTN_CREATE_FOLLOWUP,
    BTN_DASHBOARD,
    BTN_DUE_RENEWALS,
    BTN_EXPIRED_POLICIES,
    BTN_EXPIRING_10_DAYS,
    BTN_EXPIRING_POLICIES,
    BTN_FOLLOWUPS,
    BTN_HELP,
    BTN_KPI_SUMMARY,
    BTN_PENDING_FOLLOWUPS,
    BTN_PENDING_FOLLOWUPS_MENU,
    BTN_POLICIES,
    BTN_RECENTLY_RENEWED,
    BTN_RENEWALS,
    BTN_TODAY_FOLLOWUPS,
    BTN_TOTAL_POLICIES,
    CB_ACTION_KPI,
    CB_ACTION_POLICIES_DUE,
    CB_ACTION_RENEWALS_DUE,
    CB_MAIN_DASHBOARD,
    CB_MAIN_HELP,
    CB_MENU_MAIN,
    MENU_CHOOSE_LINE,
    MenuKind,
    inline_keyboard,
    menu_context_store,
    parse_callback_data,
    widen_label,
)


@pytest.fixture(autouse=True)
def clear_menu_store():
    menu_context_store._menus.clear()
    yield
    menu_context_store._menus.clear()


def _row_labels(markup) -> list[list[str]]:
    return [[btn.text.rstrip() for btn in row] for row in markup.inline_keyboard]


def test_widen_label_adds_spacing_after_emoji():
    assert widen_label(BTN_DASHBOARD) == "📊  Dashboard"


def test_main_inline_keyboard_layout():
    markup = inline_keyboard(MenuKind.MAIN)
    labels = _row_labels(markup)
    callbacks = [[btn.callback_data for btn in row] for row in markup.inline_keyboard]
    assert labels[0] == [widen_label(BTN_DASHBOARD), widen_label(BTN_POLICIES)]
    assert labels[1] == [widen_label(BTN_RENEWALS), widen_label(BTN_FOLLOWUPS)]
    assert labels[2] == [widen_label(BTN_HELP)]
    assert callbacks[0] == ["dashboard", "policies"]
    assert callbacks[1] == ["renewals", "followups"]
    assert callbacks[2] == ["help"]


def test_policies_inline_keyboard_layout():
    markup = inline_keyboard(MenuKind.POLICIES)
    labels = _row_labels(markup)
    assert labels[0] == [widen_label(BTN_TOTAL_POLICIES), widen_label(BTN_ACTIVE_POLICIES)]
    assert labels[1] == [widen_label(BTN_DUE_RENEWALS), widen_label(BTN_EXPIRING_POLICIES)]
    assert labels[2] == [widen_label(BTN_EXPIRED_POLICIES)]
    assert labels[3] == [widen_label(BTN_BACK)]


def test_dashboard_inline_keyboard_layout():
    markup = inline_keyboard(MenuKind.DASHBOARD)
    labels = _row_labels(markup)
    assert len(labels[0]) == 2
    assert labels[0][0] == widen_label(BTN_KPI_SUMMARY)
    assert labels[1] == [widen_label(BTN_PENDING_FOLLOWUPS)]
    assert labels[2] == [widen_label(BTN_BACK)]


def test_renewals_inline_keyboard_layout():
    markup = inline_keyboard(MenuKind.RENEWALS)
    labels = _row_labels(markup)
    assert labels[0] == [widen_label(BTN_DUE_RENEWALS), widen_label(BTN_EXPIRING_10_DAYS)]
    assert labels[1] == [widen_label(BTN_RECENTLY_RENEWED)]
    assert labels[2] == [widen_label(BTN_BACK)]


def test_followups_inline_keyboard_layout():
    markup = inline_keyboard(MenuKind.FOLLOWUPS)
    labels = _row_labels(markup)
    assert labels[0] == [widen_label(BTN_PENDING_FOLLOWUPS_MENU), widen_label(BTN_TODAY_FOLLOWUPS)]
    assert labels[1] == [widen_label(BTN_CREATE_FOLLOWUP)]
    assert labels[2] == [widen_label(BTN_BACK)]


def test_two_column_rows_balance_button_width():
    markup = inline_keyboard(MenuKind.MAIN)
    first_row = markup.inline_keyboard[0]
    assert len(first_row[0].text) == len(first_row[1].text)


def test_parse_callback_open_dashboard():
    result = parse_callback_data(CB_MAIN_DASHBOARD)
    assert result is not None
    assert result.menu == MenuKind.DASHBOARD
    assert "Dashboard" in result.prompt
    assert MENU_CHOOSE_LINE in result.prompt


def test_parse_callback_back():
    result = parse_callback_data(CB_MENU_MAIN)
    assert result is not None
    assert result.prompt.startswith("🏠 Main Menu")
    assert MENU_CHOOSE_LINE in result.prompt


def test_parse_callback_execute_kpi():
    result = parse_callback_data(CB_ACTION_KPI)
    assert result is not None
    assert result.action == "dashboard.kpi"
    assert result.menu == MenuKind.DASHBOARD


def test_due_renewals_separate_callbacks():
    policy_result = parse_callback_data(CB_ACTION_POLICIES_DUE)
    renewal_result = parse_callback_data(CB_ACTION_RENEWALS_DUE)
    assert policy_result.action == "policies.due_renewals"
    assert renewal_result.action == "renewals.due_renewals"


def test_parse_callback_help():
    result = parse_callback_data(CB_MAIN_HELP)
    assert result is not None
    assert result.action == "main.help"
    assert result.menu == MenuKind.MAIN
