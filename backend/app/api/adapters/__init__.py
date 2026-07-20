"""Request-body adapters for external module integrations."""

from app.api.adapters.claims_reminder_config import (
    adapt_claims_reminder_config_payload,
    adapt_claims_reminder_config_payload_async,
    is_claims_integration_payload,
)

__all__ = [
    "adapt_claims_reminder_config_payload",
    "adapt_claims_reminder_config_payload_async",
    "is_claims_integration_payload",
]
