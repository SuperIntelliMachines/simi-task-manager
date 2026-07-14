"""Reusable InsurancePolicy query helpers."""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from app.models.verticals import InsurancePolicy


def select_insurance_policies(*, load_custom_reminders: bool = False) -> Select[tuple[InsurancePolicy]]:
    """Policy query; optionally eager-load custom_reminders for detail/edit endpoints."""
    query = select(InsurancePolicy)
    if load_custom_reminders:
        query = query.options(selectinload(InsurancePolicy.custom_reminders))
    return query
