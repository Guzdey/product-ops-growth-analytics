"""Contract tests for the dependency-free Goal 1 CLI."""

from __future__ import annotations

import json

import pytest

from product_ops.cli import COMMANDS, build_parser, main
from product_ops.config import DEFAULT_RAW_DATA_DIR, OFFICIAL_DATASET_FILES


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


@pytest.mark.parametrize("command", ["metrics", "export"])
def test_later_commands_are_safe_full_dataset_placeholders(
    command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main([command, "--json"])

    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["command"] == command
    assert result["status"] == "planned"
    assert result["side_effects"] == "none"
    assert result["dataset_scope"] == "official-full-dataset"
    assert result["data_origin"] == "retailrocket"
    assert result["raw_data_dir"] == str(DEFAULT_RAW_DATA_DIR)
    assert result["required_files"] == list(OFFICIAL_DATASET_FILES)
    assert result["sample_is_default_input"] is False


def test_demo_mode_is_never_labelled_as_official_data(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "demo.json"
    config_path.write_text(
        json.dumps(
            {
                "data_home": "/tmp/product-ops/demo-fixture",
                "demo_mode": True,
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["metrics", "--config", str(config_path), "--json"])

    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["dataset_scope"] == "synthetic-demo-fixture"
    assert result["data_origin"] == "synthetic"
    assert result["required_files"] == []
    assert result["sample_is_default_input"] is False


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
