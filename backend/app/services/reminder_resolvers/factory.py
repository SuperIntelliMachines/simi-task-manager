"""Factory for reminder entity resolvers."""

from __future__ import annotations

from app.services.reminder_resolvers.base import ReminderEntityResolver, UnsupportedReminderEntityTypeError
from app.services.reminder_resolvers.metadata import ReminderModuleMetadata, ReminderModuleSummary
from app.services.reminder_resolvers.registry import get_registered_resolver, get_registered_resolvers, load_resolver_plugins


class ReminderResolverFactory:
    """Resolve module-specific entity handlers via the auto-registration registry."""

    def __init__(self, resolvers: dict[str, ReminderEntityResolver] | None = None) -> None:
        self._overrides = resolvers

    @classmethod
    def get(cls, entity_type: str) -> ReminderEntityResolver:
        return get_registered_resolver(entity_type)

    @classmethod
    def supported_entity_types(cls) -> tuple[str, ...]:
        load_resolver_plugins()
        return tuple(sorted(get_registered_resolvers().keys()))

    @classmethod
    def list_module_metadata(cls) -> list[ReminderModuleMetadata]:
        """Return metadata for every registered resolver (for Reminder Management)."""
        load_resolver_plugins()
        resolvers = get_registered_resolvers()
        return [resolvers[key].metadata() for key in sorted(resolvers.keys())]

    @classmethod
    def list_module_summaries(cls) -> list[ReminderModuleSummary]:
        return [
            ReminderModuleSummary(
                id=meta.id,
                name=meta.name,
                supports_date=meta.supports_date,
                supports_workflow=meta.supports_workflow,
            )
            for meta in cls.list_module_metadata()
        ]

    @classmethod
    def get_module_metadata(cls, entity_type: str) -> ReminderModuleMetadata:
        return cls.get(entity_type).metadata()

    def resolve(self, entity_type: str) -> ReminderEntityResolver:
        """Instance lookup; supports optional test overrides."""
        if self._overrides is not None:
            key = (entity_type or "").strip().lower()
            resolver = self._overrides.get(key)
            if resolver is None:
                raise UnsupportedReminderEntityTypeError(key)
            return resolver
        return self.get(entity_type)


_default_factory: ReminderResolverFactory | None = None


def get_reminder_resolver_factory() -> ReminderResolverFactory:
    global _default_factory
    if _default_factory is None:
        _default_factory = ReminderResolverFactory()
    return _default_factory
