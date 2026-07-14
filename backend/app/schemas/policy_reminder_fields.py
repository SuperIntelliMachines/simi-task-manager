"""Shared Pydantic field parsing for policy reminder DND times."""

from __future__ import annotations

from datetime import time

from pydantic import field_serializer, field_validator

from app.utils.policy_reminder_settings import parse_time_hhmm


class PolicyDndTimeFieldsMixin:
    dnd_start_time: time | None = None
    dnd_end_time: time | None = None

    @field_validator("dnd_start_time", mode="before")
    @classmethod
    def parse_dnd_start_time(cls, value: object) -> time | None:  # type: ignore[override]
        return parse_time_hhmm(value, field_name="dnd_start_time")  # type: ignore[arg-type]

    @field_validator("dnd_end_time", mode="before")
    @classmethod
    def parse_dnd_end_time(cls, value: object) -> time | None:  # type: ignore[override]
        return parse_time_hhmm(value, field_name="dnd_end_time")  # type: ignore[arg-type]


class PolicyDndTimeResponseMixin:
    dnd_start_time: time | None = None
    dnd_end_time: time | None = None

    @field_serializer("dnd_start_time", "dnd_end_time")
    def serialize_dnd_times(self, value: time | None) -> str | None:
        if value is None:
            return None
        return value.strftime("%H:%M")
