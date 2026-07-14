from app.utils.user_display import format_user_display_name


def test_format_user_display_name_from_email():
    assert format_user_display_name("uday.kumar@example.com") == "Uday Kumar"


def test_format_user_display_name_fallback():
    assert format_user_display_name("") == "SIMI Insurance"
    assert format_user_display_name(None) == "SIMI Insurance"
