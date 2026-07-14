"""Claims integration package — read-only Gyantr AI Claims API access."""

from app.integrations.claims.client import ClaimsClient
from app.integrations.claims.service import ClaimsIntegrationService, get_claims_integration_service

__all__ = [
    "ClaimsClient",
    "ClaimsIntegrationService",
    "get_claims_integration_service",
]
