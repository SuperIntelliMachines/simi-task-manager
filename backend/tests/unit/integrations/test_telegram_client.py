from app.channels.telegram_settings import normalize_telegram_connection_settings, resolve_telegram_bot_token


def test_resolve_telegram_bot_token_prefers_connection_settings():
    assert resolve_telegram_bot_token({"botToken": " ui-token "}) == "ui-token"
    assert resolve_telegram_bot_token({"bot_token": "snake-token"}) == "snake-token"


def test_normalize_telegram_connection_settings_adds_bot_token():
    normalized = normalize_telegram_connection_settings({"botToken": "ui-token"})
    assert normalized["bot_token"] == "ui-token"
