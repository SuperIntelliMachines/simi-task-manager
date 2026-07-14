"""Unit tests for organization dependency label mapping."""

from app.core.organization_dependency_labels import (
    RELATED_BUSINESS_DATA_LABEL,
    build_dependency_items,
    label_for_table,
)


def test_known_tables_map_to_friendly_labels():
    assert label_for_table("contacts") == "Contacts"
    assert label_for_table("reminder_configs") == "Reminder Configurations"
    assert label_for_table("users") == "Users"


def test_unknown_tables_never_expose_raw_names():
    assert label_for_table("some_future_module_table") == RELATED_BUSINESS_DATA_LABEL


def test_build_dependency_items_aggregates_shared_labels():
    items = build_dependency_items(
        [
            {"table": "reminder_configs", "count": 2},
            {"table": "reminder_instances", "count": 3},
            {"table": "contacts", "count": 9},
            {"table": "unknown_xyz", "count": 1},
        ]
    )
    assert items == [
        {"label": "Contacts", "count": 9},
        {"label": "Reminders", "count": 3},
        {"label": "Reminder Configurations", "count": 2},
        {"label": RELATED_BUSINESS_DATA_LABEL, "count": 1},
    ]
