"""Storage-policy and dependency-free configuration tests."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from product_ops.config import (
    DEFAULT_DATA_HOME,
    DEFAULT_PARQUET_DIRECTORY,
    DEFAULT_RAW_DATA_DIR,
    DEFAULT_WAREHOUSE_DIRECTORY,
    ConfigError,
    ProjectConfig,
    load_project_config,
)


def test_default_uses_official_full_dataset_on_d_drive(monkeypatch) -> None:
    monkeypatch.delenv("PRODUCT_OPS_DATA_HOME", raising=False)
    monkeypatch.delenv("PRODUCT_OPS_DEMO_MODE", raising=False)
    config = load_project_config()

    assert config.data_home == DEFAULT_DATA_HOME
    assert config.raw_data_dir == DEFAULT_RAW_DATA_DIR
    assert config.raw_data_dir == PureWindowsPath(
        r"D:\CodexData\product-ops-growth-analytics\raw\extracted"
    )
    assert config.warehouse_directory == DEFAULT_WAREHOUSE_DIRECTORY
    assert config.parquet_directory == DEFAULT_PARQUET_DIRECTORY
    assert config.demo_mode is False


def test_ci_data_home_environment_override_is_honored(monkeypatch) -> None:
    monkeypatch.setenv(
        "PRODUCT_OPS_DATA_HOME", "/tmp/product-ops/ci-environment-fixture"
    )
    monkeypatch.setenv("PRODUCT_OPS_DEMO_MODE", "true")

    config = load_project_config()

    assert config.data_home == PurePosixPath(
        "/tmp/product-ops/ci-environment-fixture"
    )
    assert config.raw_data_dir == PurePosixPath(
        "/tmp/product-ops/ci-environment-fixture/raw/extracted"
    )
    assert config.warehouse_directory == PurePosixPath(
        "/tmp/product-ops/ci-environment-fixture/warehouse"
    )
    assert config.parquet_directory == PurePosixPath(
        "/tmp/product-ops/ci-environment-fixture/parquet"
    )
    assert config.demo_mode is True


def test_flat_yaml_is_supported_without_pyyaml(tmp_path) -> None:
    config_path = tmp_path / "project.yaml"
    config_path.write_text(
        "\n".join(
            [
                r"data_home: D:\CodexData\another-product-ops-project",
                "analysis_timezone: UTC",
                "session_gap_minutes: 45",
                "synthetic_seed: 42",
                "demo_mode: false",
            ]
        ),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.raw_data_dir == PureWindowsPath(
        r"D:\CodexData\another-product-ops-project\raw\extracted"
    )
    assert config.session_gap_minutes == 45
    assert config.synthetic_seed == 42


def test_documented_toml_sections_are_supported(tmp_path) -> None:
    config_path = tmp_path / "project.toml"
    config_path.write_text(
        "\n".join(
            [
                "[paths]",
                'data_home = "D:/CodexData/toml-project"',
                "[project]",
                'analysis_timezone = "UTC"',
                "session_gap_minutes = 30",
                "synthetic_seed = 20260809",
                "demo_mode = false",
            ]
        ),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.data_home == PureWindowsPath(r"D:\CodexData\toml-project")
    assert config.raw_data_dir == PureWindowsPath(
        r"D:\CodexData\toml-project\raw\extracted"
    )


def test_json_config_can_override_derived_paths(tmp_path) -> None:
    config_path = tmp_path / "project.json"
    config_path.write_text(
        json.dumps(
            {
                "data_home": r"D:\CodexData\json-project",
                "raw_data_dir": r"D:\CodexData\json-project\raw\official",
            }
        ),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.raw_data_dir == PureWindowsPath(
        r"D:\CodexData\json-project\raw\official"
    )


def test_database_default_follows_custom_warehouse_directory() -> None:
    config = ProjectConfig.from_mapping(
        {
            "data_home": r"D:\CodexData\custom-layout",
            "warehouse_directory": r"D:\CodexData\custom-layout\duckdb",
        }
    )

    assert config.database_path == PureWindowsPath(
        r"D:\CodexData\custom-layout\duckdb\product_ops.duckdb"
    )


@pytest.mark.parametrize("unsafe_home", ["C:\\", "D:\\"])
def test_drive_root_is_always_rejected(unsafe_home: str) -> None:
    with pytest.raises(ConfigError, match="root"):
        ProjectConfig.from_mapping({"data_home": unsafe_home, "demo_mode": True})


def test_full_mode_rejects_c_drive_project_directory() -> None:
    with pytest.raises(ConfigError, match="must be on D"):
        ProjectConfig.from_mapping(
            {"data_home": r"C:\Temp\product-ops-test", "demo_mode": False}
        )


def test_demo_mode_allows_dedicated_posix_fixture_directory() -> None:
    config = ProjectConfig.from_mapping(
        {"data_home": "/tmp/product-ops/fixture", "demo_mode": True}
    )

    assert config.data_home == PurePosixPath("/tmp/product-ops/fixture")
    assert config.raw_data_dir == PurePosixPath(
        "/tmp/product-ops/fixture/raw/extracted"
    )


def test_ci_does_not_turn_posix_fixture_into_full_dataset(monkeypatch) -> None:
    monkeypatch.setenv("CI", "true")

    with pytest.raises(ConfigError, match="full-mode data_home"):
        ProjectConfig.from_mapping(
            {"data_home": "/tmp/product-ops/ci-fixture", "demo_mode": False}
        )


def test_child_path_cannot_escape_data_home() -> None:
    with pytest.raises(ConfigError, match="inside data_home"):
        ProjectConfig.from_mapping(
            {
                "data_home": r"D:\CodexData\product-ops-test",
                "raw_data_dir": r"D:\OtherProject\raw\extracted",
            }
        )


def test_child_path_rejects_parent_directory_traversal() -> None:
    with pytest.raises(ConfigError, match="traversal"):
        ProjectConfig.from_mapping(
            {
                "data_home": r"D:\CodexData\product-ops-test",
                "raw_data_dir": (
                    r"D:\CodexData\product-ops-test\raw\..\..\other-project"
                ),
            }
        )


@pytest.mark.parametrize("broad_path", [Path.home(), Path.cwd()])
def test_user_home_and_workspace_root_are_rejected(broad_path: Path) -> None:
    with pytest.raises(ConfigError):
        ProjectConfig.from_mapping(
            {"data_home": str(broad_path), "demo_mode": True}
        )


def test_unknown_keys_fail_fast() -> None:
    with pytest.raises(ConfigError, match="Unknown configuration"):
        ProjectConfig.from_mapping({"sample_csv": "desktop-sample.csv"})


def test_repository_example_config_matches_loader_contract() -> None:
    config_path = Path(__file__).resolve().parents[1] / "config" / "project.example.toml"

    config = load_project_config(config_path)

    assert config.data_home == DEFAULT_DATA_HOME
    assert config.raw_data_dir == DEFAULT_RAW_DATA_DIR
    assert config.warehouse_directory == DEFAULT_WAREHOUSE_DIRECTORY
    assert config.parquet_directory == DEFAULT_PARQUET_DIRECTORY
    assert config.demo_mode is False
