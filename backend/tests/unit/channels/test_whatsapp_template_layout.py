from app.channels.whatsapp_template_layout import (
    TemplateLayout,
    build_template_components,
    normalize_template_language,
    resolve_template_language,
    resolve_template_layout,
)


def test_welcome_layout_has_no_body_params():
    layout = resolve_template_layout("welcome", None)
    assert layout == TemplateLayout(components=())


def test_welcome_static_template_ignores_template_variables():
    layout = resolve_template_layout("welcome", None)
    components = build_template_components(
        layout,
        {
            "customer_name": "Uday",
            "entity_label": "Policy Renewal",
            "reminder_date": "30-07-2026 02:30 PM",
            "sender_name": "ABC Insurance",
        },
    )
    assert components == []


def test_policy_renewal_reminder_layout_uses_four_body_params():
    layout = resolve_template_layout("policy_renewal_reminder", None)
    components = build_template_components(
        layout,
        {
            "customer_name": "Uday",
            "entity_label": "Policy Renewal",
            "reminder_date": "30-07-2026 02:30 PM",
            "sender_name": "ABC Insurance",
        },
    )
    assert components == [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": "Uday"},
                {"type": "text", "text": "Policy Renewal"},
                {"type": "text", "text": "30-07-2026 02:30 PM"},
                {"type": "text", "text": "ABC Insurance"},
            ],
        }
    ]


def test_connection_template_layout_override_supports_header_and_body():
    layout = resolve_template_layout(
        "welcome",
        {
            "templateLayout": {
                "language": "en_GB",
                "components": [
                    {"type": "header", "format": "text", "param_keys": ["customer_name"]},
                    {"type": "body", "param_keys": ["customer_name"]},
                ],
            }
        },
    )
    components = build_template_components(layout, {"customer_name": "Uday"})
    assert components == [
        {
            "type": "header",
            "parameters": [{"type": "text", "text": "Uday"}],
        },
        {
            "type": "body",
            "parameters": [{"type": "text", "text": "Uday"}],
        },
    ]


def test_connection_template_layout_with_empty_param_keys_sends_no_components():
    layout = resolve_template_layout(
        "welcome",
        {
            "templateLayout": {
                "components": [{"type": "body", "param_keys": []}],
            }
        },
    )
    assert build_template_components(layout, {"customer_name": "Uday"}) == []


def test_unknown_template_has_no_components_by_default():
    layout = resolve_template_layout("custom_template", None)
    assert layout == TemplateLayout(components=())
    assert build_template_components(layout, {"customer_name": "Uday"}) == []


def test_policy_renewal_reminder_resolves_to_en_us_language():
    language = resolve_template_language("policy_renewal_reminder", {}, env_language="en")
    assert language == "en_US"


def test_policy_renewal_reminder_ignores_connection_generic_en():
    language = resolve_template_language(
        "policy_renewal_reminder",
        {"language": "en"},
        env_language="en",
    )
    assert language == "en_US"


def test_normalize_template_language_maps_en_us_to_en_for_welcome():
    assert normalize_template_language("en_US", "welcome") == "en"


def test_resolve_template_language_uses_env_when_connection_has_no_language():
    language = resolve_template_language(
        "welcome",
        {},
        env_language="en",
    )
    assert language == "en"


def test_resolve_template_language_prefers_template_layout_language():
    language = resolve_template_language(
        "welcome",
        {"templateLayout": {"language": "en_GB"}},
        env_language="en",
    )
    assert language == "en_GB"


def test_resolve_template_language_normalizes_connection_en_us_for_welcome():
    language = resolve_template_language(
        "welcome",
        {"language": "en_US"},
        env_language="en",
    )
    assert language == "en"


def test_resolve_template_language_prefers_function_arg():
    language = resolve_template_language(
        "welcome",
        {"language": "en_US", "templateLayout": {"language": "en_GB"}},
        template_language="en",
        env_language="fr",
    )
    assert language == "en"
