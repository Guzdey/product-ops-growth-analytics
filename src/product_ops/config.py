"""Dependency-free project configuration and storage safety checks.

This module only resolves and validates project paths; it never ingests data by
itself. Keeping it in the standard library ensures that ``product-ops --help``
remains available before DuckDB, Streamlit, or PyYAML are installed.
"""

from __future__ import annotations

import json
import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any

DEFAULT_DATA_HOME = PureWindowsPath(
    r"D:\CodexData\product-ops-growth-analytics"
)
DEFAULT_RAW_DATA_DIR = DEFAULT_DATA_HOME / "raw" / "extracted"
DEFAULT_WAREHOUSE_DIRECTORY = DEFAULT_DATA_HOME / "warehouse"
DEFAULT_DATABASE_PATH = DEFAULT_WAREHOUSE_DIRECTORY / "product_ops.duckdb"
DEFAULT_PARQUET_DIRECTORY = DEFAULT_DATA_HOME / "parquet"
DEFAULT_TEMP_DIRECTORY = DEFAULT_DATA_HOME / "tmp"
DEFAULT_EXPORT_DIRECTORY = DEFAULT_DATA_HOME / "exports"
OFFICIAL_DATASET_FILES = (
    "events.csv",
    "item_properties_part1.csv",
    "item_properties_part2.csv",
    "category_tree.csv",
)

_PATH_KEYS = (
    "data_home",
    "raw_data_dir",
    "warehouse_directory",
    "database_path",
    "parquet_directory",
    "temp_directory",
    "export_directory",
)
_CONFIG_KEYS = frozenset(
    (*_PATH_KEYS, "analysis_timezone", "session_gap_minutes", "synthetic_seed", "demo_mode")
)
_TOML_METADATA_KEYS = {
    "project": frozenset({"name"}),
    "paths": frozenset(),
}


class ConfigError(ValueError):
    """Raised when project configuration is missing, malformed, or unsafe."""


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Validated configuration for the local full-dataset workflow.

    Full mode uses :class:`~pathlib.PureWindowsPath` because the authoritative
    data location is on the user's D drive. Demo/CI fixtures may use a dedicated
    :class:`~pathlib.PurePosixPath`. Goal 1 never opens either kind of path.
    """

    data_home: PurePath = DEFAULT_DATA_HOME
    raw_data_dir: PurePath = DEFAULT_RAW_DATA_DIR
    warehouse_directory: PurePath = DEFAULT_WAREHOUSE_DIRECTORY
    database_path: PurePath = DEFAULT_DATABASE_PATH
    parquet_directory: PurePath = DEFAULT_PARQUET_DIRECTORY
    temp_directory: PurePath = DEFAULT_TEMP_DIRECTORY
    export_directory: PurePath = DEFAULT_EXPORT_DIRECTORY
    analysis_timezone: str = "UTC"
    session_gap_minutes: int = 30
    synthetic_seed: int = 20260809
    demo_mode: bool = False

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> ProjectConfig:
        """Build and validate a config from a flat mapping.

        When ``data_home`` changes, dependent paths are derived from the new
        location unless they are explicitly supplied.
        """

        unknown = sorted(set(values) - _CONFIG_KEYS)
        if unknown:
            names = ", ".join(unknown)
            raise ConfigError(f"Unknown configuration key(s): {names}")

        home = _portable_path(values.get("data_home", DEFAULT_DATA_HOME), "data_home")
        demo_mode = _boolean_value(values.get("demo_mode", False), "demo_mode")
        warehouse_directory = _portable_path(
            values.get("warehouse_directory", home / "warehouse"),
            "warehouse_directory",
        )
        config = cls(
            data_home=home,
            raw_data_dir=_portable_path(
                values.get("raw_data_dir", home / "raw" / "extracted"),
                "raw_data_dir",
            ),
            warehouse_directory=warehouse_directory,
            database_path=_portable_path(
                values.get(
                    "database_path", warehouse_directory / "product_ops.duckdb"
                ),
                "database_path",
            ),
            parquet_directory=_portable_path(
                values.get("parquet_directory", home / "parquet"),
                "parquet_directory",
            ),
            temp_directory=_portable_path(
                values.get("temp_directory", home / "tmp"), "temp_directory"
            ),
            export_directory=_portable_path(
                values.get("export_directory", home / "exports"),
                "export_directory",
            ),
            analysis_timezone=str(values.get("analysis_timezone", "UTC")).strip(),
            session_gap_minutes=_integer_value(
                values.get("session_gap_minutes", 30), "session_gap_minutes"
            ),
            synthetic_seed=_integer_value(
                values.get("synthetic_seed", 20260809), "synthetic_seed"
            ),
            demo_mode=demo_mode,
        )
        validate_project_config(config)
        return config

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return {
            "data_home": str(self.data_home),
            "raw_data_dir": str(self.raw_data_dir),
            "warehouse_directory": str(self.warehouse_directory),
            "database_path": str(self.database_path),
            "parquet_directory": str(self.parquet_directory),
            "temp_directory": str(self.temp_directory),
            "export_directory": str(self.export_directory),
            "analysis_timezone": self.analysis_timezone,
            "session_gap_minutes": self.session_gap_minutes,
            "synthetic_seed": self.synthetic_seed,
            "demo_mode": self.demo_mode,
        }


def load_project_config(config_path: str | os.PathLike[str] | None = None) -> ProjectConfig:
    """Load TOML, JSON, or a deliberately small, flat subset of YAML.

    ``PRODUCT_OPS_DATA_HOME`` and ``PRODUCT_OPS_DEMO_MODE`` can override missing
    file settings. The overrides are subject to the same storage safety checks.
    No configured directory is created by this function.
    """

    values: dict[str, Any] = {}
    if config_path is not None:
        path = Path(config_path)
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise ConfigError(f"Cannot read config file '{path}': {exc}") from exc
        values = _parse_config_text(text, suffix=path.suffix.lower())

    env_data_home = os.getenv("PRODUCT_OPS_DATA_HOME")
    if "data_home" not in values and env_data_home:
        values["data_home"] = env_data_home
    env_demo_mode = os.getenv("PRODUCT_OPS_DEMO_MODE")
    if "demo_mode" not in values and env_demo_mode:
        values["demo_mode"] = env_demo_mode

    return ProjectConfig.from_mapping(values)


def validate_project_config(config: ProjectConfig) -> None:
    """Reject paths that could grow on C or target overly broad locations."""

    _validate_data_home(config.data_home, demo_mode=config.demo_mode)
    for key in _PATH_KEYS[1:]:
        path = getattr(config, key)
        _validate_child_path(path, config.data_home, key)

    if not config.analysis_timezone:
        raise ConfigError("analysis_timezone must not be empty")
    if config.session_gap_minutes <= 0:
        raise ConfigError("session_gap_minutes must be greater than zero")
    if config.synthetic_seed < 0:
        raise ConfigError("synthetic_seed must be zero or greater")


def _validate_data_home(path: PurePath, *, demo_mode: bool) -> None:
    if not path.is_absolute():
        raise ConfigError("data_home must be an absolute path")
    if ".." in path.parts:
        raise ConfigError("data_home must not contain parent-directory traversal")
    if path == type(path)(path.anchor):
        raise ConfigError("data_home cannot be a filesystem or drive root")
    if len(path.parts) < 3:
        raise ConfigError("data_home is too broad; use a dedicated project directory")

    if isinstance(path, PureWindowsPath):
        if not path.drive:
            raise ConfigError("data_home must include a Windows drive")
        if path.drive.casefold() != "d:" and not demo_mode:
            raise ConfigError(
                "full-mode data_home must be on D; use demo_mode for small fixtures"
            )
    elif not demo_mode:
        raise ConfigError(
            "full-mode data_home must use the Windows D drive; "
            "use demo_mode for small fixtures"
        )

    _reject_broad_local_target(path)


def _validate_child_path(path: PurePath, data_home: PurePath, key: str) -> None:
    if not path.is_absolute():
        raise ConfigError(f"{key} must be an absolute path")
    if ".." in path.parts:
        raise ConfigError(f"{key} must not contain parent-directory traversal")
    if type(path) is not type(data_home):
        raise ConfigError(f"{key} must use the same path style as data_home")
    try:
        relative = path.relative_to(data_home)
    except ValueError as exc:
        raise ConfigError(f"{key} must stay inside data_home") from exc
    if not relative.parts:
        raise ConfigError(f"{key} must not equal data_home")


def _portable_path(value: Any, key: str) -> PurePath:
    if isinstance(value, PurePath):
        return value
    if not isinstance(value, (str, os.PathLike)):
        raise ConfigError(f"{key} must be a path string")
    text = os.fspath(value).strip()
    if not text:
        raise ConfigError(f"{key} must not be empty")
    if _looks_like_windows_path(text):
        return PureWindowsPath(text)
    return PurePosixPath(text)


def _looks_like_windows_path(value: str) -> bool:
    return (
        len(value) >= 3
        and value[0].isalpha()
        and value[1] == ":"
        and value[2] in {"\\", "/"}
    ) or value.startswith("\\\\")


def _reject_broad_local_target(path: PurePath) -> None:
    """Reject the current workspace and user home as broad data roots."""

    candidates: list[PurePath] = []
    if isinstance(path, PureWindowsPath) and os.name == "nt":
        candidates.extend([PureWindowsPath(Path.home()), PureWindowsPath(Path.cwd())])
    elif isinstance(path, PurePosixPath) and os.name != "nt":
        candidates.extend([PurePosixPath(Path.home()), PurePosixPath(Path.cwd())])
    if path in candidates:
        raise ConfigError("data_home cannot equal the user home or workspace root")


def _integer_value(value: Any, key: str) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"{key} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{key} must be an integer") from exc


def _boolean_value(value: Any, key: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "on", "1"}:
            return True
        if normalized in {"false", "no", "off", "0"}:
            return False
    raise ConfigError(f"{key} must be a boolean")


def _parse_config_text(text: str, *, suffix: str) -> dict[str, Any]:
    stripped = text.lstrip()
    if suffix == ".toml":
        try:
            parsed_toml = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"Invalid TOML configuration: {exc}") from exc
        return _flatten_toml(parsed_toml)
    if suffix == ".json" or stripped.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Invalid JSON configuration: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ConfigError("Configuration must be a JSON object")
        return parsed
    return _parse_flat_yaml(text)


def _flatten_toml(parsed: Mapping[str, Any]) -> dict[str, Any]:
    """Read documented settings while allowing explicit descriptive metadata."""

    values: dict[str, Any] = {}
    for key, value in parsed.items():
        if key in {"paths", "project"}:
            if not isinstance(value, dict):
                raise ConfigError(f"TOML section [{key}] must be a table")
            for nested_key, nested_value in value.items():
                if nested_key in _TOML_METADATA_KEYS[key]:
                    continue
                if nested_key not in _CONFIG_KEYS:
                    raise ConfigError(
                        f"Unknown configuration key '{nested_key}' in [{key}]"
                    )
                if nested_key in values:
                    raise ConfigError(f"Duplicate configuration key '{nested_key}'")
                values[nested_key] = nested_value
        elif key in {"dataset", "warehouse"}:
            if not isinstance(value, dict):
                raise ConfigError(f"TOML section [{key}] must be a table")
            # These sections document the source contract and future warehouse
            # settings. Goal 1 does not execute or interpret either section.
            continue
        else:
            if isinstance(value, dict):
                raise ConfigError(f"Unknown TOML section [{key}]")
            if key not in _CONFIG_KEYS:
                raise ConfigError(f"Unknown configuration key '{key}'")
            values[key] = value
    return values


def _parse_flat_yaml(text: str) -> dict[str, Any]:
    """Parse top-level ``key: scalar`` YAML without third-party dependencies."""

    values: dict[str, Any] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw_line[:1].isspace():
            raise ConfigError(
                f"Nested YAML is not supported (line {line_number}); use flat keys"
            )
        if ":" not in raw_line:
            raise ConfigError(f"Expected 'key: value' on line {line_number}")
        key, raw_value = raw_line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key or not raw_value:
            raise ConfigError(f"Empty key or value on line {line_number}")
        if key in values:
            raise ConfigError(f"Duplicate configuration key '{key}'")
        values[key] = _parse_scalar(raw_value)
    return values


def _parse_scalar(value: str) -> Any:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        if value[0] == '"':
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return value[1:-1]

    normalized = value.casefold()
    if normalized in {"true", "yes", "on"}:
        return True
    if normalized in {"false", "no", "off"}:
        return False
    if normalized in {"null", "none", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        return value
