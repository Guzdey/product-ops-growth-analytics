"""Unified dependency-free CLI for the project milestones."""

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
    "ingest": "Register the future full Retailrocket CSV ingestion workflow.",
    "build": "Register the future SQL warehouse build workflow.",
    "metrics": "Register the future operations-metric workflow.",
    "validate": "Register the future data-quality validation workflow.",
    "export": "Register the future dashboard export workflow.",
    "run-all": "Register the future end-to-end workflow.",
}


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser without importing optional project dependencies."""

    parser = argparse.ArgumentParser(
        prog="product-ops",
        description=(
            "Retailrocket user-growth analytics. Goal 1 commands are safe "
            "placeholders and do not read or write the dataset."
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
        help="Emit a machine-readable placeholder result.",
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
            help="Emit a machine-readable placeholder result.",
        )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run a registered Goal 1 placeholder command.

    No command in v0.1 opens, creates, or modifies a data file.  Implementations
    arrive in later milestones after their SQL and data-quality tests exist.
    """

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

    result = placeholder_result(args.command, config)
    if as_json:
        output.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        output.write(_format_text_result(result))
    return 0


def placeholder_result(command: str, config: ProjectConfig) -> dict[str, Any]:
    """Describe the registered command without touching the filesystem."""

    if command not in COMMANDS:
        raise ValueError(f"Unknown command: {command}")
    if config.demo_mode:
        dataset = "Synthetic demo fixture (not implemented in v0.1.0)"
        dataset_scope = "synthetic-demo-fixture"
        data_origin = "synthetic"
        required_files: list[str] = []
    else:
        dataset = "Retailrocket official full dataset"
        dataset_scope = "official-full-dataset"
        data_origin = "retailrocket"
        required_files = list(OFFICIAL_DATASET_FILES)
    return {
        "milestone": "v0.1.0",
        "command": command,
        "status": "placeholder",
        "side_effects": "none",
        "dataset": dataset,
        "dataset_scope": dataset_scope,
        "data_origin": data_origin,
        "raw_data_dir": str(config.raw_data_dir),
        "required_files": required_files,
        "sample_is_default_input": False,
        "message": (
            "Command registered for a later milestone; no data was read or written."
        ),
    }


def _format_text_result(result: dict[str, Any]) -> str:
    return (
        f"[{result['milestone']} placeholder] {result['command']} is registered.\n"
        "No data was read or written.\n"
        f"Formal input: {result['dataset']}\n"
        f"Raw data directory: {result['raw_data_dir']}\n"
        "The desktop sample is for orientation only and is not a default "
        "analysis input.\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
