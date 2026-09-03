"""Contract tests for the dependency-free Goal 1 CLI."""

from __future__ import annotations

import json

import pytest

from product_ops.cli import COMMANDS, build_parser, main


def test_help_lists_every_registered_command() -> None:
    help_text = build_parser().format_help()

    for command in COMMANDS:
        assert command in help_text


def test_help_exits_successfully_without_optional_dependencies(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["--help"])

    assert raised.value.code == 0
    assert "DuckDB" not in capsys.readouterr().err


@pytest.mark.parametrize(
    ("command", "expected_hint"),
    [("metrics", "core.fct_event"), ("export", "mart.metric_registry")],
)
def test_metric_commands_report_missing_prerequisites(
    command: str,
    expected_hint: str,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "demo.json"
    config_path.write_text(
        json.dumps(
            {
                "data_home": str(tmp_path / "metric-command-fixture"),
                "demo_mode": True,
            }
        ),
        encoding="utf-8",
    )

    exit_code = main([command, "--config", str(config_path), "--json"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert expected_hint in captured.err


def test_implemented_command_reports_missing_source_files(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "demo.json"
    config_path.write_text(
        json.dumps({"data_home": str(tmp_path / "data"), "demo_mode": True}),
        encoding="utf-8",
    )

    exit_code = main(["ingest", "--config", str(config_path)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Required source file is missing" in captured.err


def test_config_error_returns_two_without_running_command(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "unsafe.toml"
    config_path.write_text(
        '[paths]\ndata_home = "C:/"\n[project]\ndemo_mode = false\n',
        encoding="utf-8",
    )

    exit_code = main(["ingest", "--config", str(config_path)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Configuration error" in captured.err
