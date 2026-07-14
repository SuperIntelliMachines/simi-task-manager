"""Module-level reminder metadata published by each ReminderEntityResolver.

Used by Reminder Management to render forms without hardcoding Insurance/Claims
(or any other vertical) in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReminderTriggerField:
    """A date-style scheduling field the module can use as an anchor."""

    key: str
    label: str
    type: str = "date"


@dataclass(frozen=True)
class ReminderWorkflowEvent:
    """A workflow / status-stage event the module can use as an anchor."""

    key: str
    label: str


@dataclass(frozen=True)
class ReminderRecipientType:
    """A recipient role the module can resolve at send time."""

    id: str
    label: str


@dataclass(frozen=True)
class ReminderModuleMetadata:
    """Full capability catalog for one registered reminder module."""

    id: str
    name: str
    trigger_types: tuple[ReminderTriggerField, ...] = ()
    workflow_events: tuple[ReminderWorkflowEvent, ...] = ()
    recipient_types: tuple[ReminderRecipientType, ...] = ()
    supported_channels: tuple[str, ...] = ()
    default_template: str | None = None

    @property
    def supports_date(self) -> bool:
        return any((item.type or "date").lower() == "date" for item in self.trigger_types)

    @property
    def supports_workflow(self) -> bool:
        return len(self.workflow_events) > 0


@dataclass(frozen=True)
class ReminderModuleSummary:
    """Compact module row for module pickers."""

    id: str
    name: str
    supports_date: bool
    supports_workflow: bool
