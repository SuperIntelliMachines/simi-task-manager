"""Typed models for Claims API payloads.

Shapes are intentionally permissive (`extra="allow"`) so SIMI can proxy
Gyantr AI responses without owning or persisting Service Case schemas.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClaimsModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ClaimsTokenResponse(ClaimsModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int | None = None
    refresh_token: str | None = None


class ClaimsServiceCase(ClaimsModel):
    id: Any | None = None
    case_id: Any | None = None
    status: str | None = None
    title: str | None = None
    summary: str | None = None


class ClaimsServiceCaseList(ClaimsModel):
    items: list[Any] = Field(default_factory=list)
    total: int | None = None
    page: int | None = None
    page_size: int | None = None


class ClaimsStats(ClaimsModel):
    """Dashboard statistics from the Claims service."""


class ClaimsAttentionItems(ClaimsModel):
    items: list[Any] = Field(default_factory=list)


class ClaimsMetadata(ClaimsModel):
    """Lookup/metadata payload from the Claims service."""
