from __future__ import annotations

from datetime import date, datetime, time, UTC
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from app.schemas.custom_reminder_fields import CustomReminderSchema
from app.schemas.policy_reminder_fields import PolicyDndTimeFieldsMixin, PolicyDndTimeResponseMixin
from app.utils.datetime_utils import normalize_to_utc_naive
from app.utils.display_date import validate_expiry_datetime
from app.utils.policy_email import validate_policy_email
from app.utils.policy_mobile import validate_mobile_number
from app.utils.policy_reminder_settings import (
    REMINDER_TYPE_PERSONALIZED,
    validate_policy_reminder_settings,
)
from app.utils.preferred_channels import coerce_preferred_channel_input, validate_preferred_channel
from app.utils.renewal_frequency import RENEWAL_FREQUENCY_DEFAULT, validate_renewal_frequency


class PolicyCreate(PolicyDndTimeFieldsMixin, BaseModel):
    # API accepts a human-friendly `policyholder_name` and InsuranceService will
    # resolve or create a contact and set the DB `policyholder_id`.
    policyholder_name: str
    policy_number: str
    policy_type: str | None = None
    carrier: str | None = None
    renewal_frequency: str = RENEWAL_FREQUENCY_DEFAULT
    premium: Decimal | None = None
    currency: str | None = "INR"
    # Match DB: expiry is stored as a DateTime in the legacy table.
    expiry_date: datetime
    grace_period_days: int = Field(default=30, ge=0)
    assigned_agent_id: int | None = None
    preferred_channel: list[str] | str | None = None
    reminder_type: str = "default"
    reminder_unit: str | None = None
    reminder_value: int | None = None
    custom_reminders: list[CustomReminderSchema] | None = None
    mobile_number: str | None = None
    email: str | None = None
    policy_metadata: dict[str, Any] | None = None
    document_name: str | None = None
    document_path: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("policyholder_name", "policy_number")
    def not_empty(cls, v: str) -> str:  # type: ignore[override]
        v2 = v.strip()
        if not v2:
            raise ValueError("must not be empty")
        return v2

    @field_validator("premium")
    def premium_non_negative(cls, v: Decimal | None) -> Decimal | None:  # type: ignore[override]
        if v is None:
            return v
        if v < 0:
            raise ValueError("premium must be non-negative")
        return v

    @field_validator("expiry_date")
    def normalize_expiry_date(cls, v: datetime) -> datetime:  # type: ignore[override]
        return validate_expiry_datetime(v)

    @field_validator("currency")
    def currency_upper(cls, v: str | None) -> str | None:  # type: ignore[override]
        if v is None:
            return v
        v2 = v.strip().upper()
        if len(v2) > 3:
            raise ValueError("currency should be a 3-letter code")
        return v2

    @field_validator("mobile_number")
    def validate_mobile_number_field(cls, v: str | None) -> str | None:  # type: ignore[override]
        return validate_mobile_number(v)

    @field_validator("email")
    def validate_email_field(cls, v: str | None) -> str | None:  # type: ignore[override]
        return validate_policy_email(v)

    @field_validator("renewal_frequency")
    def validate_renewal_frequency_field(cls, v: str | None) -> str:  # type: ignore[override]
        if v is None:
            return RENEWAL_FREQUENCY_DEFAULT
        return validate_renewal_frequency(v)

    @field_validator("preferred_channel", mode="before")
    @classmethod
    def coerce_preferred_channel_field(cls, v: list[str] | str | None) -> list[str] | None:  # type: ignore[override]
        return coerce_preferred_channel_input(v)

    @field_validator("preferred_channel")
    @classmethod
    def validate_preferred_channel_field(cls, v: list[str] | None) -> list[str] | None:  # type: ignore[override]
        return validate_preferred_channel(v)

    @model_validator(mode="after")
    def validate_reminder_settings(self) -> "PolicyCreate":
        has_custom = bool(self.custom_reminders)
        if has_custom:
            self.reminder_type = REMINDER_TYPE_PERSONALIZED
        validated = validate_policy_reminder_settings(
            reminder_type=self.reminder_type,
            reminder_unit=self.reminder_unit,
            reminder_value=self.reminder_value,
            dnd_start_time=self.dnd_start_time,
            dnd_end_time=self.dnd_end_time,
            has_custom_reminders=has_custom,
        )
        self.reminder_type = str(validated["reminder_type"])
        self.reminder_unit = validated["reminder_unit"]  # type: ignore[assignment]
        self.reminder_value = validated["reminder_value"]  # type: ignore[assignment]
        self.dnd_start_time = validated["dnd_start_time"]  # type: ignore[assignment]
        self.dnd_end_time = validated["dnd_end_time"]  # type: ignore[assignment]
        return self


class PolicyUpdate(PolicyDndTimeFieldsMixin, BaseModel):
    # allow updating by contact id or name; callers should prefer `policyholder_id`
    policyholder_id: int | None = None
    policyholder_name: str | None = None
    policy_number: str | None = None
    policy_type: str | None = None
    carrier: str | None = None
    renewal_frequency: str | None = None
    premium: Decimal | None = None
    currency: str | None = None
    expiry_date: datetime | None = None
    grace_period_days: int | None = Field(default=None, ge=0)
    assigned_agent_id: int | None = None
    preferred_channel: list[str] | str | None = None
    reminder_type: str | None = None
    reminder_unit: str | None = None
    reminder_value: int | None = None
    custom_reminders: list[CustomReminderSchema] | None = None
    mobile_number: str | None = None
    email: str | None = None
    policy_metadata: dict[str, Any] | None = None
    document_name: str | None = None
    document_path: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("expiry_date")
    def normalize_expiry_date(cls, v: datetime | None) -> datetime | None:  # type: ignore[override]
        if v is None:
            return v
        return validate_expiry_datetime(v)

    @field_validator("premium")
    def premium_non_negative(cls, v: Decimal | None) -> Decimal | None:  # type: ignore[override]
        if v is None:
            return v
        if v < 0:
            raise ValueError("premium must be non-negative")
        return v

    @field_validator("mobile_number")
    def validate_mobile_number_field(cls, v: str | None) -> str | None:  # type: ignore[override]
        return validate_mobile_number(v)

    @field_validator("email")
    def validate_email_field(cls, v: str | None) -> str | None:  # type: ignore[override]
        return validate_policy_email(v)

    @field_validator("renewal_frequency")
    def validate_renewal_frequency_field(cls, v: str | None) -> str | None:  # type: ignore[override]
        if v is None:
            return v
        return validate_renewal_frequency(v)

    @field_validator("preferred_channel", mode="before")
    @classmethod
    def coerce_preferred_channel_field(cls, v: list[str] | str | None) -> list[str] | None:  # type: ignore[override]
        if v is None:
            return None
        return coerce_preferred_channel_input(v)

    @field_validator("preferred_channel")
    @classmethod
    def validate_preferred_channel_field(cls, v: list[str] | None) -> list[str] | None:  # type: ignore[override]
        if v is None:
            return v
        return validate_preferred_channel(v)

    @model_validator(mode="after")
    def validate_reminder_settings(self) -> "PolicyUpdate":
        if self.custom_reminders is not None:
            self.reminder_type = REMINDER_TYPE_PERSONALIZED
            validated = validate_policy_reminder_settings(
                reminder_type=self.reminder_type,
                reminder_unit=self.reminder_unit,
                reminder_value=self.reminder_value,
                dnd_start_time=self.dnd_start_time,
                dnd_end_time=self.dnd_end_time,
                has_custom_reminders=True,
            )
            self.reminder_type = str(validated["reminder_type"])
            self.reminder_unit = validated["reminder_unit"]  # type: ignore[assignment]
            self.reminder_value = validated["reminder_value"]  # type: ignore[assignment]
            self.dnd_start_time = validated["dnd_start_time"]  # type: ignore[assignment]
            self.dnd_end_time = validated["dnd_end_time"]  # type: ignore[assignment]
            return self
        if (
            self.reminder_type is None
            and self.reminder_unit is None
            and self.reminder_value is None
            and self.dnd_start_time is None
            and self.dnd_end_time is None
        ):
            return self
        validated = validate_policy_reminder_settings(
            reminder_type=self.reminder_type or "default",
            reminder_unit=self.reminder_unit,
            reminder_value=self.reminder_value,
            dnd_start_time=self.dnd_start_time,
            dnd_end_time=self.dnd_end_time,
        )
        self.reminder_type = str(validated["reminder_type"])
        self.reminder_unit = validated["reminder_unit"]  # type: ignore[assignment]
        self.reminder_value = validated["reminder_value"]  # type: ignore[assignment]
        self.dnd_start_time = validated["dnd_start_time"]  # type: ignore[assignment]
        self.dnd_end_time = validated["dnd_end_time"]  # type: ignore[assignment]
        return self


class PolicyDocumentUploadResponse(BaseModel):
    document_name: str
    document_path: str


class PolicyRenewalSmsResponse(BaseModel):
    mode: str
    mobile: str
    policyholder_name: str
    policy_number: str
    payment_link: str
    logged_in_user_name: str
    message: str
    sms_uri: str | None = None


class PolicyRenewRequest(BaseModel):
    new_expiry_date: datetime
    renewal_notes: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("new_expiry_date")
    def normalize_new_expiry_date(cls, v: datetime) -> datetime:  # type: ignore[override]
        return validate_expiry_datetime(v)

    @field_validator("renewal_notes")
    def strip_renewal_notes(cls, v: str | None) -> str | None:  # type: ignore[override]
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None


class PolicyReminderResponse(BaseModel):
    id: int
    policy_id: int
    reminder_type: str | None = None
    reminder_at: datetime
    stage: int
    stage_direction: str | None = None
    stage_unit: str | None = None
    stage_value: int | None = None
    status: str
    channel: str
    sent_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PolicyResponse(PolicyDndTimeResponseMixin, BaseModel):
    id: int
    organization_id: int
    # legacy table stores `policyholder_id` (FK to contacts)
    policyholder_id: int
    # resolved contact name for convenience
    policyholder_name: str | None = None
    mobile: str | None = None
    email: str | None = None
    policy_number: str
    policy_type: str | None = None
    carrier: str | None = None
    renewal_frequency: str | None = None
    premium: Decimal | None = None
    currency: str | None = None
    # match DB DateTime
    expiry_date: datetime
    grace_period_days: int = 30
    status: str
    # legacy field name
    assigned_agent_user_id: int | None = None
    preferred_channel: list[str] | None = None
    reminder_type: str | None = None
    reminder_unit: str | None = None
    reminder_value: int | None = None
    custom_reminders: list[CustomReminderSchema] | None = Field(default_factory=list)
    policy_metadata: dict[str, Any] | None = None
    mobile_number: str | None = None
    document_name: str | None = None
    document_path: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("custom_reminders", mode="before")
    @classmethod
    def normalize_custom_reminders(cls, value: object) -> list:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        try:
            return list(value)
        except TypeError:
            return []


class PolicyRenewResponse(BaseModel):
    policy: PolicyResponse
    reminders: list[PolicyReminderResponse] = Field(default_factory=list)


class FollowUpCreate(BaseModel):
    # allow either a reference to existing contact or a name to resolve/create
    related_policy_id: int | None = None
    contact_id: int | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    status: str | None = None
    preferred_channel: str | None = None
    followup_due_at: datetime | None = None
    assigned_agent_id: int | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("followup_due_at")
    def normalize_followup_due_at(cls, v: datetime | None) -> datetime | None:  # type: ignore[override]
        return normalize_to_utc_naive(v)

    @field_validator("contact_name")
    def name_strip(cls, v: str | None) -> str | None:  # type: ignore[override]
        return v.strip() if isinstance(v, str) else v


class FollowUpUpdate(BaseModel):
    related_policy_id: int | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    status: str | None = None
    preferred_channel: str | None = None
    followup_due_at: datetime | None = None
    assigned_agent_id: int | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("followup_due_at")
    def normalize_followup_due_at(cls, v: datetime | None) -> datetime | None:  # type: ignore[override]
        return normalize_to_utc_naive(v)


class FollowUpResponse(BaseModel):
    id: int
    organization_id: int
    related_policy_id: int | None = None
    contact_id: int | None = None
    status: str
    preferred_channel: str | None = None
    followup_due_at: datetime | None = None
    assigned_agent_user_id: int | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    customerName: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    email: str | None = None
    phone: str | None = None
    policyType: str | None = None
    followUpDate: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
