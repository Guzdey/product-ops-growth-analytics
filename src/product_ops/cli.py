"""Unified CLI for the Retailrocket analytics project."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any, TextIO

from product_ops import __version__
from product_ops.config import ConfigError, ProjectConfig, load_project_config

COMMANDS = ("ingest", "build", "metrics", "validate", "export", "run-all")

_COMMAND_HELP = {
    "ingest": "Import all four Retailrocket CSV files into explicit raw tables.",
    "build": "Build typed staging tables and reusable core warehouse models.",
    "metrics": "Calculate versioned operations metrics and hypothesis results.",
    "validate": "Run data-contract and warehouse quality checks.",
    "export": "Export privacy-safe aggregate metric tables and a summary.",
    "run-all": "Run ingest, build, metrics, validate, and export in order.",
}

IMPLEMENTED_COMMANDS = COMMANDS


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser without importing optional project dependencies."""

    parser = argparse.ArgumentParser(
        prog="product-ops",
        description=(
            "Retailrocket user-growth analytics. Goal 3 builds a full DuckDB "
            "warehouse, calculates operations metrics, and exports aggregate results."
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

    try:
        result = _run_warehouse_command(args.command, config)
    except Exception as exc:
        from product_ops.warehouse import WarehouseError

        if not isinstance(exc, WarehouseError):
            raise
        error_output.write(f"Warehouse error: {exc}\n")
        return 2
    if as_json:
        output.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        output.write(_format_text_result(result))
    return 0 if result.get("status") != "failed" else 1


def _run_warehouse_command(command: str, config: ProjectConfig) -> dict[str, Any]:
    """Import warehouse dependencies only when an implemented command runs."""

    from product_ops.metrics import calculate_metrics, export_metrics
    from product_ops.warehouse import build, ingest, run_all, validate

    functions = {
        "ingest": ingest,
        "build": build,
        "metrics": calculate_metrics,
        "validate": validate,
        "export": export_metrics,
        "run-all": run_all,
    }
    return functions[command](config)


def _format_text_result(result: dict[str, Any]) -> str:
    return (
        f"[{result['milestone']}] {result['command']}: {result['status']}\n"
        f"DuckDB: {result.get('database_path', 'see nested step results')}\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
