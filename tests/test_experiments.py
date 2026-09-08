"""Deterministic tests for the isolated v0.5 synthetic experiment workflow."""

from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb
import pytest

from product_ops.config import ProjectConfig
from product_ops.experiments import (
    EXPORT_RELATIONS,
    _generate_assignments,
    run_experiments,
)


def _config(tmp_path: Path) -> ProjectConfig:
    return ProjectConfig.from_mapping(
        {"data_home": str(tmp_path / "experiment-fixture"), "demo_mode": True}
    )


def _assignment_digest(rows: list[tuple[object, ...]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(repr(row).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def test_fixed_seed_generates_identical_isolated_assignments() -> None:
    first = _generate_assignments(20260809)
    second = _generate_assignments(20260809)
    changed = _generate_assignments(20260810)

    assert _assignment_digest(first) == _assignment_digest(second)
    assert _assignment_digest(first) != _assignment_digest(changed)
    assert len(first) == 40_000
    assert all(str(row[0]).startswith("sim_20260809_") for row in first)
    assert all(row[13] == "synthetic" for row in first)
    assert all(not row[8] or row[7] for row in first)


def test_experiment_calculates_both_scenarios_and_exports_only_aggregates(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    result = run_experiments(config)

    assert result["status"] == "success"
    assert result["participant_count"] == 40_000
    assert result["data_origin"] == "synthetic"
    assert result["summary"]["fail"] == 0

    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        results = {
            scenario: (absolute, relative, low, high, p_value, significant, decision)
            for scenario, absolute, relative, low, high, p_value, significant, decision in (
                connection.execute(
                    """
                    SELECT scenario_id, absolute_lift, relative_lift,
                           confidence_low, confidence_high, p_value,
                           is_statistically_significant, decision
                    FROM synthetic.experiment_results
                    ORDER BY scenario_id
                    """
                ).fetchall()
            )
        }
        origins = connection.execute(
            """
            SELECT DISTINCT data_origin FROM synthetic.experiment_assignment
            UNION
            SELECT DISTINCT data_origin FROM synthetic.channel_summary
            """
        ).fetchall()
        arm_counts = connection.execute(
            """
            SELECT scenario_id, experiment_group, assigned_users
            FROM synthetic.experiment_arm_metrics ORDER BY ALL
            """
        ).fetchall()
    finally:
        connection.close()

    no_effect = results["no_effect"]
    positive = results["positive_effect"]
    assert no_effect[0] == pytest.approx(0)
    assert not no_effect[5]
    assert no_effect[6] == "do_not_roll_out_based_on_current_evidence"
    assert positive[0] == pytest.approx(0.012)
    assert positive[1] == pytest.approx(0.15)
    assert positive[2] > 0
    assert positive[3] > positive[2]
    assert positive[4] < 0.05
    assert positive[5]
    assert positive[6] == "candidate_for_gradual_rollout"
    assert origins == [("synthetic",)]
    assert all(row[2] == 10_000 for row in arm_counts)

    export_directory = Path(result["export_directory"])
    exported_names = {path.name for path in export_directory.glob("synthetic__*.csv")}
    assert len(exported_names) == len(EXPORT_RELATIONS)
    assert all("assignment" not in name for name in exported_names)
    exported_headers = [
        path.read_text(encoding="utf-8").splitlines()[0]
        for path in export_directory.glob("*.csv")
    ]
    assert not any("participant" in header for header in exported_headers)
