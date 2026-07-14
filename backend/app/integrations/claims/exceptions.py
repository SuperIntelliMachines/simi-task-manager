"""Exceptions for the external Gyantr AI Claims integration."""

from __future__ import annotations


class ClaimsIntegrationError(Exception):
    """Base error for Claims integration failures."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ClaimsConfigurationError(ClaimsIntegrationError):
    """Claims settings are missing or invalid."""

    def __init__(self, message: str = "Claims integration is not configured."):
        super().__init__(message, status_code=503)


class ClaimsAuthenticationError(ClaimsIntegrationError):
    """Failed to authenticate with the Claims service."""

    def __init__(self, message: str = "Failed to authenticate with the Claims service."):
        super().__init__(message, status_code=502)


class ClaimsNotFoundError(ClaimsIntegrationError):
    """Requested Claims resource was not found."""

    def __init__(self, message: str = "Claims resource not found."):
        super().__init__(message, status_code=404)


class ClaimsTimeoutError(ClaimsIntegrationError):
    """Claims service request timed out."""

    def __init__(self, message: str = "Claims service request timed out."):
        super().__init__(message, status_code=504)


class ClaimsNetworkError(ClaimsIntegrationError):
    """Network failure talking to the Claims service."""

    def __init__(self, message: str = "Unable to reach the Claims service."):
        super().__init__(message, status_code=502)


class ClaimsAPIError(ClaimsIntegrationError):
    """Claims service returned an unexpected error response."""

    def __init__(self, message: str, *, status_code: int | None = 502):
        super().__init__(message, status_code=status_code)
