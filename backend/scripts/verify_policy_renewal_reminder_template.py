#!/usr/bin/env python3
"""
Phase A: verify policy_renewal_reminder in Meta matches the 4-parameter generic body.

Also prints WhatsApp Business Manager copy-paste instructions when verification fails.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
ENV_FILE = PROJECT_ROOT / ".env"
SCRIPTS_DIR = BACKEND_ROOT / "scripts"

sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from app.channels.whatsapp_template_specs import (  # noqa: E402
    EXPECTED_PLACEHOLDER_COUNT,
    POLICY_RENEWAL_REMINDER_BODY,
    POLICY_RENEWAL_REMINDER_BODY_EXAMPLES,
    POLICY_RENEWAL_REMINDER_LANGUAGE,
    POLICY_RENEWAL_REMINDER_PARAM_LABELS,
    POLICY_RENEWAL_REMINDER_TEMPLATE_NAME,
)
import check_whatsapp_templates as cwt  # noqa: E402


def _print_business_manager_instructions() -> None:
    examples = POLICY_RENEWAL_REMINDER_BODY_EXAMPLES[0]
    print("\n=== WhatsApp Business Manager (Phase A) ===")
    print("1. Open Meta Business Suite -> WhatsApp Manager -> Message templates")
    print(f"2. Edit template: {POLICY_RENEWAL_REMINDER_TEMPLATE_NAME}")
    print(f"3. Language: {POLICY_RENEWAL_REMINDER_LANGUAGE}")
    print("4. Replace BODY with:\n")
    for line in POLICY_RENEWAL_REMINDER_BODY.splitlines():
        print(f"   {line}")
    print("\n5. Parameter labels / samples:")
    for index, (label, sample) in enumerate(
        zip(POLICY_RENEWAL_REMINDER_PARAM_LABELS, examples, strict=True),
        start=1,
    ):
        print(f"   {{{{{index}}}}} {label} - example: {sample}")
    print("6. Submit for review and wait for status APPROVED")
    print("7. Re-run this script to confirm")
    print("===========================================\n")


def _find_template(rows: list[dict], *, name: str, language: str) -> dict | None:
    for row in rows:
        if str(row.get("name", "")) == name and str(row.get("language", "")) == language:
            return row
    return None


def main() -> int:
    cwt.load_env_file(ENV_FILE)
    print(f"Env file: {ENV_FILE}")
    print(
        f"Checking Meta template {POLICY_RENEWAL_REMINDER_TEMPLATE_NAME!r} "
        f"({POLICY_RENEWAL_REMINDER_LANGUAGE}) for Phase A generic body"
    )

    try:
        access_token, business_account_id, api_version = cwt.validate_env()
        templates = cwt.fetch_whatsapp_templates(
            access_token=access_token,
            business_account_id=business_account_id,
            api_version=api_version,
        )
    except cwt.WhatsAppTemplateError as exc:
        print(f"\nERROR: {exc}\n", file=sys.stderr)
        _print_business_manager_instructions()
        return 1

    match = _find_template(
        templates,
        name=POLICY_RENEWAL_REMINDER_TEMPLATE_NAME,
        language=POLICY_RENEWAL_REMINDER_LANGUAGE,
    )
    if match is None:
        print(
            f"\nNOT FOUND: {POLICY_RENEWAL_REMINDER_TEMPLATE_NAME} "
            f"({POLICY_RENEWAL_REMINDER_LANGUAGE}) in this WABA.\n"
        )
        _print_business_manager_instructions()
        return 1

    body_text = cwt.extract_body_text(match.get("components"))
    placeholder_count = cwt.count_placeholders(body_text)
    status = str(match.get("status", "-"))
    normalized_actual = " ".join(body_text.split())
    normalized_expected = " ".join(POLICY_RENEWAL_REMINDER_BODY.split())
    body_matches = normalized_actual == normalized_expected
    placeholders_ok = placeholder_count == EXPECTED_PLACEHOLDER_COUNT
    approved = status.upper() == "APPROVED"
    kindly_ok = "Kindly take note" in body_text

    print("\n=== Current Meta template ===")
    print(f"name:              {match.get('name')}")
    print(f"language:          {match.get('language')}")
    print(f"status:            {status}")
    print(f"placeholder_count: {placeholder_count} (expected {EXPECTED_PLACEHOLDER_COUNT})")
    print("body_text:")
    for line in body_text.splitlines() or ["(empty)"]:
        print(f"  {line}")
    print()

    checks = [
        ("4 placeholders", placeholders_ok),
        ("body text matches Phase A spec", body_matches),
        ("contains 'Kindly take note'", kindly_ok),
        ("status APPROVED", approved),
    ]
    all_ok = all(passed for _, passed in checks)
    for label, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")

    if all_ok:
        print("\nPhase A complete: Meta template is ready for Phase B (generic reminder flow).\n")
        return 0

    print("\nPhase A incomplete: update template in Meta Business Manager, then re-run.\n")
    if not body_matches or not placeholders_ok or not kindly_ok:
        _print_business_manager_instructions()
    elif not approved:
        print("Template body looks correct but is not APPROVED yet. Wait for Meta review.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
