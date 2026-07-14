"""Auto-registration registry for reminder entity resolvers."""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING, TypeVar

from app.services.reminder_resolvers.base import ReminderEntityResolver, UnsupportedReminderEntityTypeError

if TYPE_CHECKING:
    from collections.abc import Callable

ResolverT = TypeVar("ResolverT", bound=ReminderEntityResolver)

_REGISTRY: dict[str, ReminderEntityResolver] = {}
_RESOLVER_CLASSES: dict[str, type[ReminderEntityResolver]] = {}
_PLUGINS_LOADED = False


def _ensure_registry_instances() -> None:
    for key, cls in _RESOLVER_CLASSES.items():
        _REGISTRY[key] = cls()


def register_resolver(entity_type: str | None = None) -> Callable[[type[ResolverT]], type[ResolverT]]:
    """
    Class decorator that registers a resolver for plug-and-play module support.

    Example::

        @register_resolver("policy")
        class PolicyReminderResolver(ReminderEntityResolver):
            ...
    """

    def decorator(cls: type[ResolverT]) -> type[ResolverT]:
        key = (entity_type or getattr(cls, "entity_type", "")).strip().lower()
        if not key:
            raise ValueError(f"resolver {cls.__name__} requires entity_type")

        cls.entity_type = key
        _RESOLVER_CLASSES[key] = cls
        _REGISTRY[key] = cls()
        return cls

    return decorator


def load_resolver_plugins() -> None:
    """Import resolver modules so @register_resolver decorators run."""
    global _PLUGINS_LOADED
    if not _PLUGINS_LOADED:
        package_name = "app.services.reminder_resolvers"
        package = importlib.import_module(package_name)
        skip = {"base", "factory", "registry", "__init__"}

        for module_info in pkgutil.iter_modules(package.__path__):
            if module_info.name in skip or module_info.name.endswith("_test"):
                continue
            importlib.import_module(f"{package_name}.{module_info.name}")

        _PLUGINS_LOADED = True

    _ensure_registry_instances()


def get_registered_resolver(entity_type: str) -> ReminderEntityResolver:
    load_resolver_plugins()
    key = (entity_type or "").strip().lower()
    resolver = _REGISTRY.get(key)
    if resolver is None:
        raise UnsupportedReminderEntityTypeError(key)
    return resolver


def get_registered_resolvers() -> dict[str, ReminderEntityResolver]:
    load_resolver_plugins()
    return dict(_REGISTRY)


def clear_resolver_registry_for_tests() -> None:
    """Drop resolver instances only; class registrations are preserved."""
    _REGISTRY.clear()
