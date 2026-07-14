"""Pydantic schemas for the generic reminder engine."""

from __future__ import annotations

from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import (
    DEFAULT_REMINDER_ANCHOR_KEY,
    ReminderAnchorType,
    ReminderOffsetDirection,
)
from app.utils.policy_reminder_settings import parse_time_hhmm
from app.utils.reminder_config_validation import (
    ReminderSchedulingValidationError,
    validate_anchor_fields,
    validate_scheduling_fields,
)


class ReminderConfigCreateBody(BaseModel):
    organization_id: int
    entity_type: str
    entity_id: int
    reminders: list["ReminderDefinitionBody"] | None = None
    # backward-compatible legacy payload
    channel: str | None = None
    offsets: list[int] | None = None
    offset_unit: str = "days"
    # Optional top-level defaults for legacy channel×offsets create
    anchor_type: str = ReminderAnchorType.DATE.value
    anchor_key: str = DEFAULT_REMINDER_ANCHOR_KEY
    offset_direction: str = ReminderOffsetDirection.BEFORE.value
    dnd_start: time | None = None
    dnd_end: time | None = None

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if not normalized:
            raise ValueError("entity_type must not be empty")
        return normalized

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = (value or "").strip().lower()
        if not normalized:
            raise ValueError("channel must not be empty")
        return normalized

    @field_validator("offsets")
    @classmethod
    def validate_offsets(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("offsets must contain at least one value")
        normalized: list[int] = []
        for offset in value:
            if int(offset) < 0:
                raise ValueError("offsets must be non-negative integers")
            normalized.append(int(offset))
        return normalized

    @field_validator("offset_unit")
    @classmethod
    def validate_offset_unit(cls, value: str) -> str:
        normalized = (value or "days").strip().lower()
        if normalized not in {"hours", "days", "weeks", "months"}:
            raise ValueError("offset_unit must be one of: hours, days, weeks, months")
        return normalized

    @model_validator(mode="before")
    @classmethod
    def normalize_anchor_defaults(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        try:
            anchor_type, anchor_key, offset_direction = validate_anchor_fields(
                anchor_type=data.get("anchor_type"),
                anchor_key=data.get("anchor_key"),
                offset_direction=data.get("offset_direction"),
            )
        except ReminderSchedulingValidationError as exc:
            raise ValueError(str(exc)) from exc
        data["anchor_type"] = anchor_type
        data["anchor_key"] = anchor_key
        data["offset_direction"] = offset_direction
        return data

    @field_validator("dnd_start", mode="before")
    @classmethod
    def parse_dnd_start(cls, value: object) -> time | None:
        return parse_time_hhmm(value, field_name="dnd_start")  # type: ignore[arg-type]

    @field_validator("dnd_end", mode="before")
    @classmethod
    def parse_dnd_end(cls, value: object) -> time | None:
        return parse_time_hhmm(value, field_name="dnd_end")  # type: ignore[arg-type]

    @model_validator(mode="after")
    def validate_payload_shape(self) -> "ReminderConfigCreateBody":
        if self.reminders is not None:
            if len(self.reminders) == 0:
                raise ValueError("reminders must contain at least one value")
            seen: set[
                tuple[str, str, str, int | None, str, str | None, tuple[str, ...]]
            ] = set()
            for reminder in self.reminders:
                key = (
                    reminder.anchor_type,
                    reminder.anchor_key,
                    reminder.offset_direction,
                    reminder.offset_value,
                    reminder.offset_unit,
                    reminder.time_of_day.isoformat() if reminder.time_of_day else None,
                    tuple(sorted(reminder.channels)),
                )
                if key in seen:
                    raise ValueError("duplicate reminder configuration detected")
                seen.add(key)
            return self
        if self.channel is None or self.offsets is None:
            raise ValueError("legacy create requires channel and offsets when reminders are not provided")
        return self


class ReminderConfigResponse(BaseModel):
    id: int
    organization_id: int
    entity_type: str
    entity_id: int
    channel: str
    template_key: str | None = None
    entity_label: str | None = None
    sender_name: str | None = None
    anchor_type: str
    anchor_key: str
    offset_direction: str
    offset_value: int
    offset_unit: str
    time_of_day: time | None = None
    scheduled_at: datetime | None = None
    dnd_start: time | None = None
    dnd_end: time | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def map_absolute_scheduled_at(cls, value: object) -> object:
        if isinstance(value, dict):
            data = dict(value)
            if "scheduled_at" not in data and "absolute_scheduled_at" in data:
                data["scheduled_at"] = data.get("absolute_scheduled_at")
            return data
        if hasattr(value, "absolute_scheduled_at"):
            return {
                "id": value.id,
                "organization_id": value.organization_id,
                "entity_type": value.entity_type,
                "entity_id": value.entity_id,
                "channel": value.channel,
                "template_key": value.template_key,
                "entity_label": value.entity_label,
                "sender_name": value.sender_name,
                "anchor_type": getattr(value, "anchor_type", ReminderAnchorType.DATE.value),
                "anchor_key": getattr(value, "anchor_key", DEFAULT_REMINDER_ANCHOR_KEY),
                "offset_direction": getattr(
                    value, "offset_direction", ReminderOffsetDirection.BEFORE.value
                ),
                "offset_value": value.offset_value,
                "offset_unit": value.offset_unit,
                "time_of_day": value.time_of_day,
                "scheduled_at": value.absolute_scheduled_at,
                "dnd_start": value.dnd_start,
                "dnd_end": value.dnd_end,
                "is_active": value.is_active,
                "created_at": value.created_at,
                "updated_at": value.updated_at,
            }
        return value


class ReminderOffsetBody(BaseModel):
    offset_value: int
    offset_unit: str = "days"
    time_of_day: time | None = None
    anchor_type: str = ReminderAnchorType.DATE.value
    anchor_key: str = DEFAULT_REMINDER_ANCHOR_KEY
    offset_direction: str = ReminderOffsetDirection.BEFORE.value

    @field_validator("offset_value")
    @classmethod
    def validate_offset_value(cls, value: int) -> int:
        if int(value) < 0:
            raise ValueError("offset_value must be >= 0")
        return int(value)

    @field_validator("offset_unit")
    @classmethod
    def validate_offset_unit(cls, value: str) -> str:
        normalized = (value or "days").strip().lower()
        if normalized not in {"hours", "days", "weeks", "months"}:
            raise ValueError("offset_unit must be one of: hours, days, weeks, months")
        return normalized

    @field_validator("time_of_day", mode="before")
    @classmethod
    def parse_time_of_day(cls, value: object) -> time | None:
        return parse_time_hhmm(value, field_name="time_of_day")  # type: ignore[arg-type]

    @model_validator(mode="before")
    @classmethod
    def normalize_anchor_defaults(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        try:
            anchor_type, anchor_key, offset_direction = validate_anchor_fields(
                anchor_type=data.get("anchor_type"),
                anchor_key=data.get("anchor_key"),
                offset_direction=data.get("offset_direction"),
            )
        except ReminderSchedulingValidationError as exc:
            raise ValueError(str(exc)) from exc
        data["anchor_type"] = anchor_type
        data["anchor_key"] = anchor_key
        data["offset_direction"] = offset_direction
        return data

    @model_validator(mode="after")
    def validate_anchor_fields_after(self) -> ReminderOffsetBody:
        try:
            self.anchor_type, self.anchor_key, self.offset_direction = validate_anchor_fields(
                anchor_type=self.anchor_type,
                anchor_key=self.anchor_key,
                offset_direction=self.offset_direction,
            )
        except ReminderSchedulingValidationError as exc:
            raise ValueError(str(exc)) from exc
        return self


class ReminderDefinitionBody(BaseModel):
    """One reminder rule with its own channels and scheduling mode."""

    channels: list[str]
    offset_value: int | None = None
    offset_unit: str = "days"
    time_of_day: time | None = None
    scheduled_at: datetime | None = None
    anchor_type: str = ReminderAnchorType.DATE.value
    anchor_key: str = DEFAULT_REMINDER_ANCHOR_KEY
    offset_direction: str = ReminderOffsetDirection.BEFORE.value

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, value: list[str]) -> list[str]:
        normalized = [(channel or "").strip().lower() for channel in value if (channel or "").strip()]
        if not normalized:
            raise ValueError("channels must contain at least one value")
        return normalized

    @field_validator("time_of_day", mode="before")
    @classmethod
    def parse_time_of_day(cls, value: object) -> time | None:
        return parse_time_hhmm(value, field_name="time_of_day")  # type: ignore[arg-type]

    @model_validator(mode="before")
    @classmethod
    def normalize_anchor_defaults(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        try:
            anchor_type, anchor_key, offset_direction = validate_anchor_fields(
                anchor_type=data.get("anchor_type"),
                anchor_key=data.get("anchor_key"),
                offset_direction=data.get("offset_direction"),
            )
        except ReminderSchedulingValidationError as exc:
            raise ValueError(str(exc)) from exc
        data["anchor_type"] = anchor_type
        data["anchor_key"] = anchor_key
        data["offset_direction"] = offset_direction
        return data

    @model_validator(mode="after")
    def validate_scheduling_mode(self) -> ReminderDefinitionBody:
        try:
            self.anchor_type, self.anchor_key, self.offset_direction = validate_anchor_fields(
                anchor_type=self.anchor_type,
                anchor_key=self.anchor_key,
                offset_direction=self.offset_direction,
            )
            validate_scheduling_fields(
                offset_value=self.offset_value,
                offset_unit=self.offset_unit,
                time_of_day=self.time_of_day,
                absolute_scheduled_at=self.scheduled_at,
            )
        except ReminderSchedulingValidationError as exc:
            raise ValueError(str(exc)) from exc
        return self


class ReminderSettingsSaveBody(BaseModel):
    """UI-driven save for all reminder_configs on one entity."""

    organization_id: int
    entity_type: str
    entity_id: int
    channels: list[str] = Field(default_factory=list)
    offsets: list[ReminderOffsetBody] = Field(default_factory=list)
    reminders: list[ReminderDefinitionBody] | None = None
    # Deprecated: reminder configs no longer rely on template_key.
    template_key: str | None = None
    entity_label: str | None = None
    sender_name: str | None = None
    # Optional entity-level defaults applied when offsets omit anchor fields
    anchor_type: str = ReminderAnchorType.DATE.value
    anchor_key: str = DEFAULT_REMINDER_ANCHOR_KEY
    offset_direction: str = ReminderOffsetDirection.BEFORE.value
    dnd_start: time | None = None
    dnd_end: time | None = None

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if not normalized:
            raise ValueError("entity_type must not be empty")
        return normalized

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, value: list[str]) -> list[str]:
        return [(channel or "").strip().lower() for channel in value if (channel or "").strip()]

    @model_validator(mode="before")
    @classmethod
    def normalize_anchor_defaults(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        try:
            anchor_type, anchor_key, offset_direction = validate_anchor_fields(
                anchor_type=data.get("anchor_type"),
                anchor_key=data.get("anchor_key"),
                offset_direction=data.get("offset_direction"),
            )
        except ReminderSchedulingValidationError as exc:
            raise ValueError(str(exc)) from exc
        data["anchor_type"] = anchor_type
        data["anchor_key"] = anchor_key
        data["offset_direction"] = offset_direction
        return data

    @field_validator("dnd_start", mode="before")
    @classmethod
    def parse_dnd_start(cls, value: object) -> time | None:
        return parse_time_hhmm(value, field_name="dnd_start")  # type: ignore[arg-type]

    @field_validator("dnd_end", mode="before")
    @classmethod
    def parse_dnd_end(cls, value: object) -> time | None:
        return parse_time_hhmm(value, field_name="dnd_end")  # type: ignore[arg-type]

    @model_validator(mode="after")
    def validate_request_shape(self) -> ReminderSettingsSaveBody:
        if self.reminders is not None:
            return self
        if self.offsets and not self.channels:
            raise ValueError("channels must contain at least one value when offsets are provided")
        return self


class ReminderEntityTypesResponse(BaseModel):
    entity_types: list[str] = Field(default_factory=list)


class ReminderConfigCreateResponse(BaseModel):
    configs: list[ReminderConfigResponse] = Field(default_factory=list)


class ReminderConfigGroupResponse(BaseModel):
    config_id: int
    organization_id: int
    entity_type: str
    entity_id: int
    anchor_type: str = ReminderAnchorType.DATE.value
    anchor_key: str = DEFAULT_REMINDER_ANCHOR_KEY
    offset_direction: str = ReminderOffsetDirection.BEFORE.value
    offset_value: int
    offset_unit: str
    time_of_day: time | None = None
    channels: list[str] = Field(default_factory=list)
    is_active: bool


class ReminderConfigGroupListResponse(BaseModel):
    configs: list[ReminderConfigGroupResponse] = Field(default_factory=list)


class ReminderConfigUpdateBody(BaseModel):
    offset_value: int | None = None
    offset_unit: str | None = None
    channel: str | None = None
    channels: list[str] | None = None
    time_of_day: time | None = None
    scheduled_at: datetime | None = None
    anchor_type: str | None = None
    anchor_key: str | None = None
    offset_direction: str | None = None
    dnd_start: time | None = None
    dnd_end: time | None = None
    is_active: bool | None = None

    @field_validator("offset_value")
    @classmethod
    def validate_offset_value(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if int(value) < 0:
            raise ValueError("offset_value must be >= 0")
        return int(value)

    @field_validator("offset_unit")
    @classmethod
    def validate_offset_unit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in {"hours", "days", "weeks", "months"}:
            raise ValueError("offset_unit must be one of: hours, days, weeks, months")
        return normalized

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("channel must not be empty")
        return normalized

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = [(channel or "").strip().lower() for channel in value if (channel or "").strip()]
        if not normalized:
            raise ValueError("channels must contain at least one value")
        return normalized

    @field_validator("time_of_day", mode="before")
    @classmethod
    def parse_time_of_day(cls, value: object) -> time | None:
        return parse_time_hhmm(value, field_name="time_of_day")  # type: ignore[arg-type]

    @field_validator("dnd_start", mode="before")
    @classmethod
    def parse_dnd_start(cls, value: object) -> time | None:
        return parse_time_hhmm(value, field_name="dnd_start")  # type: ignore[arg-type]

    @field_validator("dnd_end", mode="before")
    @classmethod
    def parse_dnd_end(cls, value: object) -> time | None:
        return parse_time_hhmm(value, field_name="dnd_end")  # type: ignore[arg-type]

    @model_validator(mode="after")
    def validate_anchor_and_scheduling(self) -> ReminderConfigUpdateBody:
        provided = self.model_dump(exclude_unset=True)
        if any(key in provided for key in ("anchor_type", "anchor_key", "offset_direction")):
            try:
                if "anchor_type" in provided:
                    self.anchor_type = validate_anchor_fields(
                        anchor_type=provided.get("anchor_type"),
                    )[0]
                if "anchor_key" in provided:
                    self.anchor_key = validate_anchor_fields(
                        anchor_key=provided.get("anchor_key"),
                    )[1]
                if "offset_direction" in provided:
                    self.offset_direction = validate_anchor_fields(
                        offset_direction=provided.get("offset_direction"),
                    )[2]
            except ReminderSchedulingValidationError as exc:
                raise ValueError(str(exc)) from exc

        scheduling_keys = {"offset_value", "offset_unit", "time_of_day", "scheduled_at"}
        if not scheduling_keys.intersection(provided):
            return self

        has_absolute = self.scheduled_at is not None
        has_relative = any(
            key in provided and provided[key] is not None
            for key in ("offset_value", "offset_unit", "time_of_day")
        )
        if has_absolute and has_relative:
            raise ValueError("cannot mix relative offsets and scheduled_at in the same update")

        if has_absolute:
            try:
                validate_scheduling_fields(
                    offset_value=None,
                    offset_unit=None,
                    time_of_day=None,
                    absolute_scheduled_at=self.scheduled_at,
                )
            except ReminderSchedulingValidationError as exc:
                raise ValueError(str(exc)) from exc
        elif "offset_value" in provided or "offset_unit" in provided:
            try:
                validate_scheduling_fields(
                    offset_value=self.offset_value if "offset_value" in provided else 0,
                    offset_unit=self.offset_unit if "offset_unit" in provided else "days",
                    time_of_day=self.time_of_day if "time_of_day" in provided else None,
                    absolute_scheduled_at=None,
                )
            except ReminderSchedulingValidationError as exc:
                raise ValueError(str(exc)) from exc
        return self


class ReminderGenerateBody(BaseModel):
    organization_id: int
    entity_type: str | None = None
    entity_id: int | None = None
    anchor_date: datetime | None = None


class ReminderGenerateAllBody(BaseModel):
    organization_id: int | None = None


class ReminderGenerateResponse(BaseModel):
    generated: int


class ReminderProcessBody(BaseModel):
    organization_id: int


class ReminderProcessResponse(BaseModel):
    processed: int
    sent: int
    failed: int = 0


# ---------------------------------------------------------------------------
# Reminder Management metadata (Phase 2)
# ---------------------------------------------------------------------------


class ReminderModuleSummaryResponse(BaseModel):
    id: str
    name: str
    supports_date: bool
    supports_workflow: bool


class ReminderTriggerFieldResponse(BaseModel):
    key: str
    label: str
    type: str = "date"


class ReminderWorkflowEventResponse(BaseModel):
    key: str
    label: str


class ReminderRecipientTypeResponse(BaseModel):
    id: str
    label: str


class ReminderModuleSchemaResponse(BaseModel):
    trigger_types: list[ReminderTriggerFieldResponse] = Field(default_factory=list)
    workflow_events: list[ReminderWorkflowEventResponse] = Field(default_factory=list)
    recipient_types: list[ReminderRecipientTypeResponse] = Field(default_factory=list)
    supported_channels: list[str] = Field(default_factory=list)
    default_template: str | None = None


class ReminderTemplateCatalogResponse(BaseModel):
    id: str
    name: str
    channel: str
    subject: str
    body: str
    module: str | None = None
