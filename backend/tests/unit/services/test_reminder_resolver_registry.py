import pytest

from app.services.reminder_resolvers.base import ReminderEntityResolver, ReminderEntitySnapshot
from app.services.reminder_resolvers.factory import ReminderResolverFactory
from app.services.reminder_resolvers.registry import (
    clear_resolver_registry_for_tests,
    get_registered_resolvers,
    load_resolver_plugins,
    register_resolver,
)


@pytest.fixture
def clean_registry():
    clear_resolver_registry_for_tests()
    yield
    load_resolver_plugins()


def test_register_resolver_decorator_registers_class(clean_registry):
    @register_resolver("sample_module")
    class SampleReminderResolver(ReminderEntityResolver):
        entity_type = "sample_module"

        async def list_entities(self, session, organization_id: int) -> list[ReminderEntitySnapshot]:
            return []

        async def get_entity(self, session, organization_id: int, entity_id: int) -> ReminderEntitySnapshot | None:
            return None

    resolvers = get_registered_resolvers()
    assert "sample_module" in resolvers
    assert isinstance(resolvers["sample_module"], SampleReminderResolver)


def test_load_resolver_plugins_discovers_policy_resolver():
    load_resolver_plugins()
    resolvers = get_registered_resolvers()
    assert "policy" in resolvers


def test_load_resolver_plugins_discovers_claims_resolver():
    load_resolver_plugins()
    resolvers = get_registered_resolvers()
    assert "claims" in resolvers


def test_factory_get_returns_registered_resolver():
    load_resolver_plugins()
    resolver = ReminderResolverFactory.get("policy")
    assert resolver.entity_type == "policy"
    claims = ReminderResolverFactory.get("claims")
    assert claims.entity_type == "claims"


def test_factory_get_unknown_entity_type_raises():
    load_resolver_plugins()
    with pytest.raises(KeyError):
        ReminderResolverFactory.get("not_registered_type")
