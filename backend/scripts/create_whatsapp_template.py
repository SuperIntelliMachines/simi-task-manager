#!/usr/bin/env python3
"""Register the policy_renewal_reminder WhatsApp template via Meta Graph API."""

from __future__ import annotations

import json
import os
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

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
ENV_FILE = PROJECT_ROOT / ".env"

sys.path.insert(0, str(BACKEND_ROOT))

from app.channels.whatsapp_template_specs import (  # noqa: E402
    POLICY_RENEWAL_REMINDER_BODY,
    POLICY_RENEWAL_REMINDER_BODY_EXAMPLES,
    POLICY_RENEWAL_REMINDER_CATEGORY,
    POLICY_RENEWAL_REMINDER_LANGUAGE,
    POLICY_RENEWAL_REMINDER_TEMPLATE_NAME,
)

DEFAULT_API_VERSION = "v22.0"
TEMPLATE_NAME = POLICY_RENEWAL_REMINDER_TEMPLATE_NAME
TEMPLATE_CATEGORY = POLICY_RENEWAL_REMINDER_CATEGORY
TEMPLATE_LANGUAGE = POLICY_RENEWAL_REMINDER_LANGUAGE
TEMPLATE_BODY = POLICY_RENEWAL_REMINDER_BODY
TEMPLATE_BODY_EXAMPLES = POLICY_RENEWAL_REMINDER_BODY_EXAMPLES


class WhatsAppTemplateError(Exception):
    """Raised when template registration fails."""


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


def create_whatsapp_template(
    *,
    access_token: str,
    business_account_id: str,
    api_version: str = DEFAULT_API_VERSION,
    name: str = TEMPLATE_NAME,
    category: str = TEMPLATE_CATEGORY,
    language: str = TEMPLATE_LANGUAGE,
    body_text: str = TEMPLATE_BODY,
    body_examples: list[list[str]] | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """
    Create a WhatsApp message template on Meta Graph API.

    Note: Meta usually rejects duplicate name+language. For an existing approved template,
    edit the body in WhatsApp Business Manager (see verify_policy_renewal_reminder_template.py).
    """
    if not access_token.strip():
        raise WhatsAppTemplateError("access_token is required")
    if not business_account_id.strip():
        raise WhatsAppTemplateError("business_account_id is required")

    url = f"https://graph.facebook.com/{api_version}/{business_account_id}/message_templates"
    payload = {
        "name": name,
        "category": category,
        "language": language,
        "components": [
            {
                "type": "BODY",
                "text": body_text,
                "example": {
                    "body_text": body_examples or TEMPLATE_BODY_EXAMPLES,
                },
            }
        ],
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        raise WhatsAppTemplateError(f"HTTP request failed: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise WhatsAppTemplateError(
            f"Invalid JSON response (status={response.status_code}): {response.text}"
        ) from exc

    if response.status_code not in {200, 201}:
        error = data.get("error", {})
        message = error.get("message", response.text)
        code = error.get("code", response.status_code)
        raise WhatsAppTemplateError(
            f"Meta API error (HTTP {response.status_code}, code={code}): {message}"
        )

    return data


def print_response(data: dict[str, Any]) -> None:
    print("\n=== Meta Graph API response ===")
    print(json.dumps(data, indent=2, sort_keys=True))
    print("===============================\n")

    template_id = data.get("id")
    status = data.get("status")
    if template_id:
        print(f"Template ID: {template_id}")
    if status:
        print(f"Status: {status} (PENDING until Meta approves)")


def main() -> int:
    load_env_file(ENV_FILE)

    print(f"Env file: {ENV_FILE}")
    print(
        f"Creating template: name={TEMPLATE_NAME} "
        f"category={TEMPLATE_CATEGORY} language={TEMPLATE_LANGUAGE}"
    )
    print(
        "If this template already exists, edit it in WhatsApp Business Manager instead "
        "(run scripts/verify_policy_renewal_reminder_template.py for instructions)."
    )

    try:
        access_token, business_account_id, api_version = validate_env()
        result = create_whatsapp_template(
            access_token=access_token,
            business_account_id=business_account_id,
            api_version=api_version,
        )
        print_response(result)
        print("Success: template submitted to Meta for review.")
        return 0
    except WhatsAppTemplateError as exc:
        print(f"\nERROR: {exc}\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
