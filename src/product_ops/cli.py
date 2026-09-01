"""Unified CLI for the Retailrocket analytics project."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any, TextIO

from product_ops import __version__
from product_ops.config import (
    OFFICIAL_DATASET_FILES,
    ConfigError,
    ProjectConfig,
    load_project_config,
)

COMMANDS = ("ingest", "build", "metrics", "validate", "export", "run-all")

_COMMAND_HELP = {
    "ingest": "Import all four Retailrocket CSV files into explicit raw tables.",
    "build": "Build typed staging tables and reusable core warehouse models.",
    "metrics": "Register the future operations-metric workflow.",
    "validate": "Run Goal 2 data-contract and warehouse quality checks.",
    "export": "Register the future dashboard export workflow.",
    "run-all": "Run Goal 2 ingest, build, and validate in order.",
}

IMPLEMENTED_COMMANDS = ("ingest", "build", "validate", "run-all")


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser without importing optional project dependencies."""

    parser = argparse.ArgumentParser(
        prog="product-ops",
        description=(
            "Retailrocket user-growth analytics. Goal 2 builds the full "
            "DuckDB warehouse; later metric and export commands remain planned."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config",
        dest="global_config",
        metavar="PATH",
        help="TOML, flat YAML, or JSON configuration (may precede the command).",
    )
    parser.add_argument(
        "--json",
        dest="global_json",
        action="store_true",
        help="Emit a machine-readable command result.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True
    for command in COMMANDS:
        subparser = subparsers.add_parser(command, help=_COMMAND_HELP[command])
        subparser.add_argument(
            "--config",
            dest="command_config",
            metavar="PATH",
            help="TOML, flat YAML, or JSON project configuration.",
        )
        subparser.add_argument(
            "--json",
            dest="command_json",
            action="store_true",
            help="Emit a machine-readable command result.",
        )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run one project command and translate expected failures to exit code 2."""

    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    args = build_parser().parse_args(argv)
    config_path = args.command_config or args.global_config
    as_json = bool(args.command_json or args.global_json)

    try:
        config = load_project_config(config_path)
    except ConfigError as exc:
        error_output.write(f"Configuration error: {exc}\n")
        return 2

    if args.command in IMPLEMENTED_COMMANDS:
        try:
            result = _run_warehouse_command(args.command, config)
        except Exception as exc:
            from product_ops.warehouse import WarehouseError

            if not isinstance(exc, WarehouseError):
                raise
            error_output.write(f"Warehouse error: {exc}\n")
            return 2
    else:
        result = planned_result(args.command, config)
    if as_json:
        output.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        output.write(_format_text_result(result))
    return 0 if result.get("status") != "failed" else 1


def planned_result(command: str, config: ProjectConfig) -> dict[str, Any]:
    """Describe a later-milestone command without touching the filesystem."""

    if command not in COMMANDS:
        raise ValueError(f"Unknown command: {command}")
    if config.demo_mode:
        dataset = "Synthetic demo fixture"
        dataset_scope = "synthetic-demo-fixture"
        data_origin = "synthetic"
        required_files: list[str] = []
    else:
        dataset = "Retailrocket official full dataset"
        dataset_scope = "official-full-dataset"
        data_origin = "retailrocket"
        required_files = list(OFFICIAL_DATASET_FILES)
    return {
        "milestone": "v0.2.0",
        "command": command,
        "status": "planned",
        "side_effects": "none",
        "dataset": dataset,
        "dataset_scope": dataset_scope,
        "data_origin": data_origin,
        "raw_data_dir": str(config.raw_data_dir),
        "required_files": required_files,
        "sample_is_default_input": False,
        "message": ("Command belongs to a later milestone; no data was read or written."),
    }


def _run_warehouse_command(command: str, config: ProjectConfig) -> dict[str, Any]:
    """Import warehouse dependencies only when an implemented command runs."""

    from product_ops.warehouse import build, ingest, run_all, validate

    functions = {
        "ingest": ingest,
        "build": build,
        "validate": validate,
        "run-all": run_all,
    }
    return functions[command](config)


def _format_text_result(result: dict[str, Any]) -> str:
    if result["status"] == "planned":
        return (
            f"[{result['milestone']} planned] {result['command']} is registered.\n"
            "No data was read or written.\n"
            f"Formal input: {result['dataset']}\n"
            f"Raw data directory: {result['raw_data_dir']}\n"
        )
    return (
        f"[{result['milestone']}] {result['command']}: {result['status']}\n"
        f"DuckDB: {result.get('database_path', 'see nested step results')}\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
