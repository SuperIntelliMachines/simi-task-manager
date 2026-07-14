"""Shared Telegram Bot API HTTP settings (proxy, timeouts, connectivity checks)."""

from __future__ import annotations

import os
import socket
from typing import Any

import httpx
from telegram.request import HTTPXRequest

from app.core.config import get_settings

# ISP DNS blocks that return sinkhole IPs instead of real Telegram endpoints.
KNOWN_BLOCKED_TELEGRAM_RESOLVES: frozenset[str] = frozenset(
    {
        "202.56.230.30",  # Airtel India RPZ (restricted.rpz.airtelspam.com)
    }
)


def resolve_telegram_proxy_url() -> str | None:
    """Proxy for Telegram API — explicit setting or standard env vars."""
    settings = get_settings()
    if settings.telegram_proxy_url.strip():
        return settings.telegram_proxy_url.strip()
    for key in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def get_telegram_api_base() -> str:
    base = get_settings().telegram_api_base_url.strip().rstrip("/")
    return base or "https://api.telegram.org"


def telegram_timeout_seconds() -> float:
    return float(get_settings().telegram_connect_timeout)


def httpx_timeout() -> httpx.Timeout:
    seconds = telegram_timeout_seconds()
    return httpx.Timeout(connect=seconds, read=seconds, write=seconds, pool=seconds)


def httpx_async_client_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {"timeout": httpx_timeout()}
    proxy = resolve_telegram_proxy_url()
    if proxy:
        kwargs["proxy"] = proxy
    return kwargs


def build_ptb_http_request() -> HTTPXRequest:
    seconds = telegram_timeout_seconds()
    return HTTPXRequest(
        connect_timeout=seconds,
        read_timeout=seconds,
        write_timeout=seconds,
        pool_timeout=seconds,
        proxy=resolve_telegram_proxy_url(),
        connection_pool_size=8,
    )


def detect_telegram_dns_block() -> str | None:
    """Return a human-readable message when ISP DNS blocks Telegram."""
    if resolve_telegram_proxy_url():
        return None
    custom_base = get_settings().telegram_api_base_url.strip()
    if custom_base and custom_base != "https://api.telegram.org":
        return None
    try:
        ip = socket.gethostbyname("api.telegram.org")
    except OSError as exc:
        return (
            f"Cannot resolve api.telegram.org ({exc}).\n"
            "Your network may block Telegram DNS lookups."
        )
    if ip in KNOWN_BLOCKED_TELEGRAM_RESOLVES:
        return (
            f"api.telegram.org resolves to {ip} (ISP DNS block — e.g. Airtel RPZ).\n"
            "Telegram is blocked on this network without a proxy or VPN."
        )
    return None


def format_telegram_connectivity_help() -> str:
    return (
        "How to fix Telegram connectivity:\n"
        "  1. Start a local VPN/proxy (Clash, V2Ray, etc.).\n"
        "  2. Add to .env:\n"
        "       TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080\n"
        "     (or http://127.0.0.1:7890 — use your proxy's host:port)\n"
        "  3. Restart: python scripts/run_telegram_bot.py\n"
        "\n"
        "Optional: change system DNS to 8.8.8.8 if only DNS is blocked.\n"
        "If direct IP is also blocked, a proxy/VPN is required."
    )


async def check_telegram_connectivity() -> tuple[bool, str]:
    """Verify outbound access to the Telegram Bot API before polling."""
    dns_issue = detect_telegram_dns_block()
    if dns_issue:
        return False, f"{dns_issue}\n\n{format_telegram_connectivity_help()}"

    base = get_telegram_api_base()
    try:
        async with httpx.AsyncClient(**httpx_async_client_kwargs()) as client:
            response = await client.get(f"{base}/")
            if response.status_code >= 500:
                return False, (
                    f"Telegram API returned HTTP {response.status_code}.\n"
                    f"{format_telegram_connectivity_help()}"
                )
    except httpx.ConnectTimeout:
        return False, (
            "Timed out connecting to the Telegram API.\n"
            f"{format_telegram_connectivity_help()}"
        )
    except httpx.ConnectError as exc:
        return False, (
            f"Cannot connect to the Telegram API ({exc}).\n"
            f"{format_telegram_connectivity_help()}"
        )
    except httpx.ProxyError as exc:
        return False, (
            f"Telegram proxy error ({exc}).\n"
            "Check TELEGRAM_PROXY_URL in .env and ensure the proxy is running."
        )
    except httpx.HTTPError as exc:
        return False, (
            f"Telegram API request failed ({exc}).\n"
            f"{format_telegram_connectivity_help()}"
        )

    proxy = resolve_telegram_proxy_url()
    if proxy:
        return True, f"Telegram API reachable via proxy ({proxy})."
    return True, "Telegram API reachable."
