"""Cross-dialect column types."""

from __future__ import annotations

import json

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import TypeDecorator


class TextArray(TypeDecorator):
    """PostgreSQL TEXT[] with JSON fallback for SQLite tests."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Text()))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        normalized = [str(item).strip().lower() for item in value if str(item).strip()]
        if dialect.name == "postgresql":
            return normalized or None
        return json.dumps(normalized)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return list(value) if value else None
        if isinstance(value, str):
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else None
        if isinstance(value, (list, tuple)):
            return list(value)
        return None
