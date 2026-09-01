"""Load and render the version-controlled DuckDB SQL models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

SQL_ROOT = Path(__file__).resolve().parents[2] / "sql"


class SqlRenderError(ValueError):
    """Raised when a SQL template is missing a required value."""


def sql_literal(value: str | Path) -> str:
    """Return a safely quoted SQL string literal."""

    return "'" + str(value).replace("'", "''") + "'"


def load_sql(relative_path: str, **values: Any) -> str:
    """Read a SQL model and replace its explicit ``{{name}}`` tokens."""

    path = SQL_ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    for name, value in values.items():
        text = text.replace("{{" + name + "}}", str(value))
        text = text.replace("{{ " + name + " }}", str(value))
    if "{{" in text or "}}" in text:
        raise SqlRenderError(f"Unresolved SQL template token in {path}")
    return text
