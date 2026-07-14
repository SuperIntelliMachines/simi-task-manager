"""Pydantic schemas for policy custom reminder rows."""

from __future__ import annotations

from datetime import time

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, model_validator

from app.utils.policy_reminder_settings import parse_time_hhmm


class CustomReminderSchema(BaseModel):
    id: int | None = None
    reminder_unit: str
    reminder_value: int
    dnd_start_time: time | None = None
    dnd_end_time: time | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("reminder_unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:  # type: ignore[override]
        normalized = (value or "").strip().lower()
        if normalized not in {"hours", "days", "weeks", "months"}:
            raise ValueError("reminder_unit must be one of: hours, days, weeks, months")
        return normalized

    @field_validator("reminder_value")
    @classmethod
    def validate_value(cls, value: int) -> int:  # type: ignore[override]
        if int(value) <= 0:
            raise ValueError("reminder_value must be a positive integer")
        return int(value)

    @field_validator("dnd_start_time", mode="before")
    @classmethod
    def parse_dnd_start_time(cls, value: object) -> time | None:  # type: ignore[override]
        return parse_time_hhmm(value, field_name="dnd_start_time")  # type: ignore[arg-type]

    @field_validator("dnd_end_time", mode="before")
    @classmethod
    def parse_dnd_end_time(cls, value: object) -> time | None:  # type: ignore[override]
        return parse_time_hhmm(value, field_name="dnd_end_time")  # type: ignore[arg-type]

    @model_validator(mode="after")
    def validate_dnd_pair(self) -> "CustomReminderSchema":
        if (self.dnd_start_time or self.dnd_end_time) and not (
            self.dnd_start_time and self.dnd_end_time
        ):
            raise ValueError("dnd_start_time and dnd_end_time must both be set")
        if (
            self.dnd_start_time
            and self.dnd_end_time
            and self.dnd_start_time == self.dnd_end_time
        ):
            raise ValueError("dnd_start_time and dnd_end_time must be different")
        return self


class CustomReminderResponse(CustomReminderSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("dnd_start_time", "dnd_end_time")
    def serialize_dnd_times(self, value: time | None) -> str | None:
        if value is None:
            return None
        return value.strftime("%H:%M")
