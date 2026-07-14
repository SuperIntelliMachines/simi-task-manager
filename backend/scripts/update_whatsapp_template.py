#!/usr/bin/env python3
"""Update the policy_renewal_reminder WhatsApp template via Meta Graph API."""

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

DEFAULT_API_VERSION = "v22.0"
PAGE_LIMIT = 100

TEMPLATE_NAME = "policy_renewal_reminder"
TEMPLATE_LANGUAGE = "en_US"
TEMPLATE_CATEGORY = "UTILITY"
TEMPLATE_BODY = (
    "Hi {{1}}, this is a reminder for your {{2}} on {{3}}. Kindly take note.\n\n"
    "Thank you,\n"
    "{{4}}"
)
# Meta rejects bodies whose last text is a variable; append static text when needed.
META_TRAILING_STATIC_SUFFIX = "\n\nKindly ignore this message if already completed."
TEMPLATE_BODY_EXAMPLES: list[list[str]] = [
    ["Ravi Kumar", "Car Insurance Renewal", "30-07-2026", "ABC Insurance"],
]
EXPECTED_PLACEHOLDER_COUNT = 4

UPDATE_NOT_SUPPORTED_MESSAGE = (
    "Template update not supported. Create a new template or edit manually in Meta Business Manager."
)
# Meta error_subcode when a variable is the first/last text in the template body.
META_TRAILING_PARAM_SUBCODE = 2388299


class WhatsAppTemplateError(Exception):
    """Raised when template update fails."""


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

    if response.status_code not in {200, 201}:
        error = data.get("error", {})
        message = error.get("message", response.text)
        code = error.get("code", response.status_code)
        raise WhatsAppTemplateError(
            f"Meta API error (HTTP {response.status_code}, code={code}): {message}"
        )

    return data


def find_template_id(
    *,
    access_token: str,
    business_account_id: str,
    api_version: str,
    name: str,
    language: str,
    timeout_seconds: float = 30.0,
) -> str:
    """Return Meta template ID for the given name and language."""
    headers = {"Authorization": f"Bearer {access_token}"}
    url: str | None = (
        f"https://graph.facebook.com/{api_version}/{business_account_id}/message_templates"
    )
    params: dict[str, Any] | None = {
        "limit": PAGE_LIMIT,
        "fields": "id,name,language,status",
        "name": name,
    }

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
            for item in batch:
                if not isinstance(item, dict):
                    continue
                if item.get("name") == name and item.get("language") == language:
                    template_id = item.get("id")
                    if template_id:
                        return str(template_id)

        url = (payload.get("paging") or {}).get("next")
        params = None

    raise WhatsAppTemplateError(
        f"Template not found: name={name!r} language={language!r}"
    )


def build_update_payload(*, body_text: str = TEMPLATE_BODY) -> dict[str, Any]:
    """Build Meta Graph API payload for template body update."""
    return {
        "category": TEMPLATE_CATEGORY,
        "components": [
            {
                "type": "BODY",
                "text": body_text,
                "example": {
                    "body_text": TEMPLATE_BODY_EXAMPLES,
                },
            }
        ],
    }


def _post_template_update(
    *,
    access_token: str,
    template_id: str,
    api_version: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> tuple[requests.Response, dict[str, Any]]:
    url = f"https://graph.facebook.com/{api_version}/{template_id}"
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
    except ValueError:
        data = {"raw_response": response.text}

    return response, data


def _raise_for_failed_update(response: requests.Response, data: dict[str, Any]) -> None:
    print("\n=== Meta Graph API response ===")
    print(json.dumps(data, indent=2, sort_keys=True))
    print("===============================\n")
    error = data.get("error", {}) if isinstance(data, dict) else {}
    subcode = error.get("error_subcode")
    if subcode == META_TRAILING_PARAM_SUBCODE:
        raise WhatsAppTemplateError(
            "Meta rejected the body: variables cannot be the first or last text in the "
            "template. Add static text after {{4}} or edit manually in Meta Business Manager."
        )
    if response.status_code in {404, 405}:
        raise WhatsAppTemplateError(UPDATE_NOT_SUPPORTED_MESSAGE)
    message = error.get("message", response.text)
    code = error.get("code", response.status_code)
    raise WhatsAppTemplateError(
        f"Meta API error (HTTP {response.status_code}, code={code}): {message}"
    )


def update_whatsapp_template(
    *,
    access_token: str,
    template_id: str,
    api_version: str = DEFAULT_API_VERSION,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """
    Update an existing WhatsApp message template on Meta Graph API.

    Meta allows POST to /{whatsapp_message_template_id} with components and category.
    """
    payload = build_update_payload(body_text=TEMPLATE_BODY)
    response, data = _post_template_update(
        access_token=access_token,
        template_id=template_id,
        api_version=api_version,
        payload=payload,
        timeout_seconds=timeout_seconds,
    )

    if response.status_code not in {200, 201}:
        error = data.get("error", {}) if isinstance(data, dict) else {}
        if error.get("error_subcode") == META_TRAILING_PARAM_SUBCODE:
            print(
                "Meta requires static text after the last variable; "
                "retrying with a closing line."
            )
            payload = build_update_payload(
                body_text=TEMPLATE_BODY + META_TRAILING_STATIC_SUFFIX,
            )
            response, data = _post_template_update(
                access_token=access_token,
                template_id=template_id,
                api_version=api_version,
                payload=payload,
                timeout_seconds=timeout_seconds,
            )

    if response.status_code not in {200, 201}:
        _raise_for_failed_update(response, data)

    return data


def print_response(data: dict[str, Any]) -> None:
    print("\n=== Meta Graph API response ===")
    print(json.dumps(data, indent=2, sort_keys=True))
    print("===============================\n")


def main() -> int:
    load_env_file(ENV_FILE)

    print(f"Env file: {ENV_FILE}")
    print(
        f"Updating template: name={TEMPLATE_NAME} "
        f"category={TEMPLATE_CATEGORY} language={TEMPLATE_LANGUAGE}"
    )
    print(f"Placeholder count: {EXPECTED_PLACEHOLDER_COUNT}")
    print(f"Body examples: {json.dumps(TEMPLATE_BODY_EXAMPLES[0])}")

    try:
        access_token, business_account_id, api_version = validate_env()
        template_id = find_template_id(
            access_token=access_token,
            business_account_id=business_account_id,
            api_version=api_version,
            name=TEMPLATE_NAME,
            language=TEMPLATE_LANGUAGE,
        )
        print(f"Found template ID: {template_id}")

        result = update_whatsapp_template(
            access_token=access_token,
            template_id=template_id,
            api_version=api_version,
        )
        print_response(result)
        print("Success: template update submitted to Meta for review.")
        return 0
    except WhatsAppTemplateError as exc:
        print(f"\nERROR: {exc}\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
