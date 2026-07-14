#!/usr/bin/env python3
"""List WhatsApp message templates from Meta Graph API."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError as exc:  # pragma: no cover - runtime guard for standalone script
    print(
        "The 'requests' package is required. Install with:\n"
        "  python -m pip install requests",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_API_VERSION = "v22.0"
PAGE_LIMIT = 100
PLACEHOLDER_PATTERN = re.compile(r"\{\{(\d+)\}\}")
HIGHLIGHT_TEMPLATE_NAME = "policy_renewal_reminder"


class WhatsAppTemplateError(Exception):
    """Raised when template listing fails."""


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ (without overwriting)."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def validate_env() -> tuple[str, str, str]:
    """Return (access_token, business_account_id, api_version) or raise."""
    access_token = (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip()
    business_account_id = (os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID") or "").strip()
    api_version = (os.getenv("WHATSAPP_API_VERSION") or DEFAULT_API_VERSION).strip() or DEFAULT_API_VERSION

    missing: list[str] = []
    if not access_token:
        missing.append("WHATSAPP_ACCESS_TOKEN")
    if not business_account_id:
        missing.append("WHATSAPP_BUSINESS_ACCOUNT_ID")

    if missing:
        raise WhatsAppTemplateError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            f"Set them in {ENV_FILE}"
        )

    return access_token, business_account_id, api_version


def _parse_response(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise WhatsAppTemplateError(
            f"Invalid JSON response (status={response.status_code}): {response.text}"
        ) from exc

    if response.status_code != 200:
        error = data.get("error", {})
        message = error.get("message", response.text)
        code = error.get("code", response.status_code)
        raise WhatsAppTemplateError(
            f"Meta API error (HTTP {response.status_code}, code={code}): {message}"
        )

    return data


def fetch_whatsapp_templates(
    *,
    access_token: str,
    business_account_id: str,
    api_version: str = DEFAULT_API_VERSION,
    timeout_seconds: float = 30.0,
) -> list[dict[str, Any]]:
    """
    Fetch all WhatsApp message templates for the business account.

    Follows Meta paging until all templates are collected.
    """
    if not access_token.strip():
        raise WhatsAppTemplateError("access_token is required")
    if not business_account_id.strip():
        raise WhatsAppTemplateError("business_account_id is required")

    headers = {"Authorization": f"Bearer {access_token}"}
    url: str | None = (
        f"https://graph.facebook.com/{api_version}/{business_account_id}/message_templates"
    )
    params: dict[str, Any] | None = {
        "limit": PAGE_LIMIT,
        "fields": "name,status,language,category,components",
    }
    templates: list[dict[str, Any]] = []

    while url:
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            raise WhatsAppTemplateError(f"HTTP request failed: {exc}") from exc

        payload = _parse_response(response)
        batch = payload.get("data")
        if isinstance(batch, list):
            templates.extend(item for item in batch if isinstance(item, dict))

        url = (payload.get("paging") or {}).get("next")
        params = None

    return templates


def extract_body_text(components: Any) -> str:
    """Return BODY component text from a template's components list."""
    if not isinstance(components, list):
        return ""

    for component in components:
        if not isinstance(component, dict):
            continue
        if str(component.get("type", "")).upper() == "BODY":
            return str(component.get("text", "")).strip()
    return ""


def count_placeholders(body_text: str) -> int:
    """Count distinct {{n}} placeholder indices in template body text."""
    if not body_text:
        return 0
    return len(set(PLACEHOLDER_PATTERN.findall(body_text)))


def summarize_template(item: dict[str, Any]) -> dict[str, Any]:
    body_text = extract_body_text(item.get("components"))
    return {
        "name": str(item.get("name", "-")),
        "status": str(item.get("status", "-")),
        "language": str(item.get("language", "-")),
        "category": str(item.get("category", "-")),
        "body_text": body_text,
        "placeholder_count": count_placeholders(body_text),
    }


def print_templates(templates: list[dict[str, Any]]) -> None:
    if not templates:
        print("\nNo WhatsApp message templates found.\n")
        return

    rows = [summarize_template(item) for item in templates]
    rows.sort(key=lambda row: row["name"].lower())

    print()
    for index, row in enumerate(rows, start=1):
        print(f"--- Template {index}/{len(rows)} ---")
        print(f"name:                {row['name']}")
        print(f"status:              {row['status']}")
        print(f"language:            {row['language']}")
        print(f"category:            {row['category']}")
        print(f"placeholder_count:   {row['placeholder_count']}")
        print("body_text:")
        if row["body_text"]:
            for line in row["body_text"].splitlines():
                print(f"  {line}")
        else:
            print("  (no BODY component)")
        print()

    print(f"Total templates: {len(rows)}")
    print()

    delivery_rows = [row for row in rows if row["name"] == HIGHLIGHT_TEMPLATE_NAME]
    if delivery_rows:
        print(f"=== {HIGHLIGHT_TEMPLATE_NAME} (exact body) ===")
        for row in delivery_rows:
            print(f"language: {row['language']}")
            print(f"status:   {row['status']}")
            print("body:")
            print(row["body_text"] if row["body_text"] else "(empty)")
            print(f"placeholders: {row['placeholder_count']}")
        print()
    else:
        print(f"Note: template '{HIGHLIGHT_TEMPLATE_NAME}' was not found in this account.\n")


def main() -> int:
    load_env_file(ENV_FILE)
    print(f"Env file: {ENV_FILE}")

    try:
        access_token, business_account_id, api_version = validate_env()
        templates = fetch_whatsapp_templates(
            access_token=access_token,
            business_account_id=business_account_id,
            api_version=api_version,
        )
        print_templates(templates)
        return 0
    except WhatsAppTemplateError as exc:
        print(f"\nERROR: {exc}\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
