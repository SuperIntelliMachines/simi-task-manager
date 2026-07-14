"""Entity resolvers for generic reminder instance generation."""

from app.services.reminder_resolvers.base import (
    ReminderEntityResolver,
    ReminderEntitySnapshot,
    UnsupportedReminderEntityTypeError,
)
from app.services.reminder_resolvers.factory import ReminderResolverFactory, get_reminder_resolver_factory
from app.services.reminder_resolvers.metadata import (
    ReminderModuleMetadata,
    ReminderModuleSummary,
    ReminderRecipientType,
    ReminderTriggerField,
    ReminderWorkflowEvent,
)
from app.services.reminder_resolvers.policy_resolver import PolicyReminderResolver
from app.services.reminder_resolvers.claims_resolver import ClaimsReminderResolver
from app.services.reminder_resolvers.registry import load_resolver_plugins, register_resolver

load_resolver_plugins()

__all__ = [
    "ClaimsReminderResolver",
    "PolicyReminderResolver",
    "ReminderEntityResolver",
    "ReminderEntitySnapshot",
    "ReminderModuleMetadata",
    "ReminderModuleSummary",
    "ReminderRecipientType",
    "ReminderResolverFactory",
    "ReminderTriggerField",
    "ReminderWorkflowEvent",
    "UnsupportedReminderEntityTypeError",
    "get_reminder_resolver_factory",
    "register_resolver",
]
