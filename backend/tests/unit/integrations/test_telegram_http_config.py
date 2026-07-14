from unittest.mock import patch

from app.integrations.telegram.http_config import (
    KNOWN_BLOCKED_TELEGRAM_RESOLVES,
    detect_telegram_dns_block,
    resolve_telegram_proxy_url,
)


def test_detect_telegram_dns_block_when_airtel_sinkhole():
    blocked_ip = next(iter(KNOWN_BLOCKED_TELEGRAM_RESOLVES))
    with patch(
        "app.integrations.telegram.http_config.socket.gethostbyname",
        return_value=blocked_ip,
    ):
        with patch(
            "app.integrations.telegram.http_config.resolve_telegram_proxy_url",
            return_value=None,
        ):
            message = detect_telegram_dns_block()
    assert message is not None
    assert "ISP DNS block" in message


def test_detect_telegram_dns_block_skipped_when_proxy_configured():
    blocked_ip = next(iter(KNOWN_BLOCKED_TELEGRAM_RESOLVES))
    with patch(
        "app.integrations.telegram.http_config.socket.gethostbyname",
        return_value=blocked_ip,
    ):
        with patch(
            "app.integrations.telegram.http_config.resolve_telegram_proxy_url",
            return_value="socks5://127.0.0.1:1080",
        ):
            assert detect_telegram_dns_block() is None


def test_resolve_telegram_proxy_url_prefers_settings(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://should-not-win:8080")
    with patch("app.integrations.telegram.http_config.get_settings") as mock_settings:
        mock_settings.return_value.telegram_proxy_url = "socks5://127.0.0.1:1080"
        assert resolve_telegram_proxy_url() == "socks5://127.0.0.1:1080"
