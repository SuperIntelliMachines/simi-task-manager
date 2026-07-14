"""WhatsApp template layout helpers for Meta Cloud API template sends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class TemplateComponentSpec:
    type: str
    param_keys: tuple[str, ...] = ()
    format: str | None = None


@dataclass(frozen=True)
class TemplateLayout:
    components: tuple[TemplateComponentSpec, ...]


# Templates approved in Meta with language code "en" (not en_US).
TEMPLATES_REGISTERED_AS_EN: frozenset[str] = frozenset({"welcome", "hello_world"})

# Meta-approved language code per template name (must match Business Manager exactly).
KNOWN_TEMPLATE_LANGUAGES: dict[str, str] = {
    "policy_renewal_reminder": "en_US",
    "welcome": "en",
    "hello_world": "en",
}

DEFAULT_TEMPLATE_LANGUAGE = "en_US"

# Presets for known approved templates. Override per connection via settings.templateLayout.
KNOWN_TEMPLATE_LAYOUTS: dict[str, TemplateLayout] = {
    # Static template — no {{1}} placeholders in Meta BODY.
    "welcome": TemplateLayout(components=()),
    "policy_renewal_reminder": TemplateLayout(
        components=(
            TemplateComponentSpec(
                type="body",
                param_keys=(
                    "customer_name",
                    "entity_label",
                    "reminder_date",
                    "sender_name",
                ),
            ),
        ),
    ),
    "hello_world": TemplateLayout(components=()),
}


def _parse_component_specs(raw_components: list[Any]) -> tuple[TemplateComponentSpec, ...]:
    specs: list[TemplateComponentSpec] = []
    for item in raw_components:
        if not isinstance(item, dict):
            continue
        component_type = str(item.get("type", "")).strip().lower()
        if component_type not in {"header", "body"}:
            continue
        raw_keys = item.get("param_keys") or item.get("paramKeys") or []
        if isinstance(raw_keys, str):
            keys = tuple(key.strip() for key in raw_keys.split(",") if key.strip())
        else:
            keys = tuple(str(key).strip() for key in raw_keys if str(key).strip())
        component_format = item.get("format")
        specs.append(
            TemplateComponentSpec(
                type=component_type,
                param_keys=keys,
                format=str(component_format).strip().lower() if component_format else None,
            )
        )
    return tuple(specs)


def normalize_template_language(language: str, template_name: str) -> str:
    code = str(language or "").strip()
    if not code:
        return KNOWN_TEMPLATE_LANGUAGES.get(template_name, DEFAULT_TEMPLATE_LANGUAGE)
    if code == "en_US" and template_name in TEMPLATES_REGISTERED_AS_EN:
        return "en"
    approved = KNOWN_TEMPLATE_LANGUAGES.get(template_name)
    if approved and code == "en" and approved != "en":
        return approved
    return code


def resolve_template_language(
    template_name: str,
    connection_settings: Mapping[str, Any] | None,
    *,
    template_language: str | None = None,
    env_language: str = "",
    fallback: str = DEFAULT_TEMPLATE_LANGUAGE,
) -> str:
    settings = connection_settings or {}
    raw_layout = settings.get("templateLayout") or settings.get("template_layout")
    layout_language = None
    if isinstance(raw_layout, dict):
        layout_language = raw_layout.get("language")

    approved_language = KNOWN_TEMPLATE_LANGUAGES.get(template_name)

    for candidate in (
        template_language,
        layout_language,
        approved_language,
        settings.get("language"),
        settings.get("templateLanguage"),
        env_language,
        fallback,
    ):
        code = str(candidate or "").strip()
        if code:
            return normalize_template_language(code, template_name)
    return normalize_template_language(fallback, template_name)


def resolve_template_layout(
    template_name: str,
    connection_settings: Mapping[str, Any] | None,
) -> TemplateLayout:
    settings = connection_settings or {}
    raw_layout = settings.get("templateLayout") or settings.get("template_layout")
    if isinstance(raw_layout, dict):
        components = _parse_component_specs(raw_layout.get("components") or [])
        return TemplateLayout(components=components)

    preset = KNOWN_TEMPLATE_LAYOUTS.get(template_name)
    if preset is not None:
        return preset

    return TemplateLayout(components=())


def _resolve_param_values(
    param_keys: tuple[str, ...],
    template_variables: Mapping[str, Any],
) -> list[str]:
    values: list[str] = []
    for key in param_keys:
        raw = template_variables.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            values.append(text)
    return values


def build_template_components(
    layout: TemplateLayout,
    template_variables: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not layout.components or not template_variables:
        return []

    components: list[dict[str, Any]] = []
    for spec in layout.components:
        if not spec.param_keys:
            continue
        values = _resolve_param_values(spec.param_keys, template_variables)
        if not values:
            continue

        if spec.type == "header":
            header_format = spec.format or "text"
            if header_format != "text":
                continue
            components.append(
                {
                    "type": "header",
                    "parameters": [{"type": "text", "text": values[0]}],
                }
            )
            continue

        components.append(
            {
                "type": "body",
                "parameters": [{"type": "text", "text": value} for value in values],
            }
        )

    return components
