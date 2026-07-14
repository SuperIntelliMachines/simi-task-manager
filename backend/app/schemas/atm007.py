from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.custom_reminder_fields import CustomReminderSchema
from app.schemas.policy_reminder_fields import PolicyDndTimeFieldsMixin

from app.utils.display_date import validate_expiry_datetime
from app.utils.policy_email import validate_policy_email
from app.utils.policy_mobile import validate_mobile_number
from app.utils.policy_reminder_settings import (
    REMINDER_TYPE_PERSONALIZED,
    validate_policy_reminder_settings,
)
from app.utils.preferred_channels import coerce_preferred_channel_input, validate_preferred_channel
from app.utils.renewal_frequency import RENEWAL_FREQUENCY_DEFAULT, validate_renewal_frequency


class InsurancePolicyCreateBody(PolicyDndTimeFieldsMixin, BaseModel):
    organization_id: int
    actor_user_id: int | None = None
    policyholder_name: str
    policy_number: str | None = None
    premium: Decimal | None = None
    policy_type: str | None = None
    carrier: str | None = None
    renewal_frequency: str = RENEWAL_FREQUENCY_DEFAULT
    assigned_agent_user_id: int | None = None
    preferred_channel: list[str] | str | None = None
    reminder_type: str = "default"
    reminder_unit: str | None = None
    reminder_value: int | None = Field(default=None, ge=1)
    custom_reminders: list[CustomReminderSchema] | None = None
    mobile_number: str | None = None
    email: str | None = None
    document_name: str | None = None
    document_path: str | None = None
    expiry_date: datetime
    grace_period_days: int = Field(default=30, ge=0)

    @field_validator("mobile_number")
    def validate_mobile_number_field(cls, v: str | None) -> str | None:  # type: ignore[override]
        return validate_mobile_number(v)

    @field_validator("email")
    def validate_email_field(cls, v: str | None) -> str | None:  # type: ignore[override]
        return validate_policy_email(v)

    @field_validator("expiry_date")
    def validate_expiry_date_field(cls, v: datetime) -> datetime:  # type: ignore[override]
        return validate_expiry_datetime(v)

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
    def validate_reminder_settings(self) -> "InsurancePolicyCreateBody":
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


class InsurancePolicyPatchBody(PolicyDndTimeFieldsMixin, BaseModel):
    actor_user_id: int | None = None
    premium: int | None = None
    policy_type: str | None = None
    carrier: str | None = None
    renewal_frequency: str | None = None
    assigned_agent_user_id: int | None = None
    preferred_channel: list[str] | str | None = None
    reminder_type: str | None = None
    reminder_unit: str | None = None
    reminder_value: int | None = Field(default=None, ge=1)
    custom_reminders: list[CustomReminderSchema] | None = None
    mobile_number: str | None = None
    email: str | None = None
    document_name: str | None = None
    document_path: str | None = None
    expiry_date: datetime | None = None
    grace_period_days: int | None = Field(default=None, ge=0)
    status: str | None = None

    @field_validator("mobile_number")
    def validate_mobile_number_field(cls, v: str | None) -> str | None:  # type: ignore[override]
        return validate_mobile_number(v)

    @field_validator("email")
    def validate_email_field(cls, v: str | None) -> str | None:  # type: ignore[override]
        return validate_policy_email(v)

    @field_validator("expiry_date")
    def validate_expiry_date_field(cls, v: datetime | None) -> datetime | None:  # type: ignore[override]
        if v is None:
            return v
        return validate_expiry_datetime(v)

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
    def validate_reminder_settings(self) -> "InsurancePolicyPatchBody":
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


class InsuranceWorkflowStartBody(BaseModel):
    actor_user_id: int | None = None


class InsuranceLeadCreateBody(BaseModel):
    organization_id: int
    actor_user_id: int | None = None
    contact_name: str
    contact_phone: str | None = None
    contact_email: str | None = None
    assigned_agent_user_id: int | None = None
    source: str | None = None
    notes: str | None = None
    demo_logged_at: datetime | None = None
    followup_due_at: datetime | None = None
    insurance_type: str | None = None
    status: str | None = None


class InsuranceLeadPatchBody(BaseModel):
    actor_user_id: int | None = None
    assigned_agent_user_id: int | None = None
    status: str | None = None
    notes: str | None = None
    followup_due_at: datetime | None = None
    related_policy_id: int | None = None


class InsuranceLeadWorkflowStartBody(BaseModel):
    actor_user_id: int | None = None
    followup_due_at: datetime | None = None
    days_until_followup: int = Field(default=3, ge=0, le=365)


class InsuranceDashboardQuery(BaseModel):
    organization_id: int
