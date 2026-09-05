"""Deterministic end-to-end tests for the v0.3 operations metrics."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import duckdb
import pytest

from product_ops.config import ProjectConfig
from product_ops.metrics import EXPORT_RELATIONS, calculate_metrics, export_metrics
from product_ops.warehouse import build, ingest, run_all


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _fixture_config(tmp_path: Path) -> ProjectConfig:
    data_home = tmp_path / "retailrocket-metric-fixture"
    raw = data_home / "raw" / "extracted"
    day = 86_400_000
    minute = 60_000
    base = 1_433_116_800_000
    events = [
        [base, 1, "view", 10, ""],
        [base + minute, 1, "addtocart", 10, ""],
        [base + 2 * minute, 1, "transaction", 10, 100],
        [base + 2 * minute, 1, "transaction", 11, 100],
        [base + 7 * day, 1, "view", 10, ""],
        [base + 8 * day, 1, "view", 10, ""],
        [base + 8 * day + minute, 1, "addtocart", 10, ""],
        [base + 8 * day + 2 * minute, 1, "transaction", 10, 101],
        [base + 5 * minute, 2, "view", 20, ""],
        [base + 6 * minute, 2, "addtocart", 20, ""],
        [base + 7 * day + minute, 2, "view", 20, ""],
        [base + 10 * minute, 3, "view", 30, ""],
        [base + 10 * minute, 3, "view", 30, ""],
        [base + 10 * minute + 1, 3, "view", 30, ""],
        [base + 15 * minute, 4, "view", 30, ""],
        [base + day, 4, "view", 30, ""],
        [base + 20 * minute, 5, "view", 10, ""],
        [base + 21 * minute, 5, "transaction", 10, 200],
        [base + 28 * day, 7, "view", 20, ""],
        [base + 29 * day, 6, "view", 30, ""],
    ]
    _write_csv(
        raw / "events.csv",
        ["timestamp", "visitorid", "event", "itemid", "transactionid"],
        events,
    )
    properties = [
        [base - day, 10, "categoryid", 2],
        [base - day, 11, "categoryid", 2],
        [base - day, 20, "categoryid", 3],
        [base - day, 30, "categoryid", 3],
        [base - day, 10, "available", 1],
        [base - day, 20, "available", 1],
    ]
    _write_csv(
        raw / "item_properties_part1.csv",
        ["timestamp", "itemid", "property", "value"],
        properties[:3],
    )
    _write_csv(
        raw / "item_properties_part2.csv",
        ["timestamp", "itemid", "property", "value"],
        properties[3:],
    )
    _write_csv(
        raw / "category_tree.csv",
        ["categoryid", "parentid"],
        [[1, ""], [2, 1], [3, 1]],
    )
    return ProjectConfig.from_mapping({"data_home": str(data_home), "demo_mode": True})


@pytest.fixture
def metric_config(tmp_path: Path) -> ProjectConfig:
    config = _fixture_config(tmp_path)
    ingest(config)
    build(config)
    return config


def test_metrics_compute_exact_activity_funnel_retention_and_transactions(
    metric_config: ProjectConfig,
) -> None:
    result = calculate_metrics(metric_config)

    failed_checks = [check for check in result["checks"] if check["status"] == "fail"]
    assert result["status"] == "success", failed_checks
    assert result["data_origin"] == "synthetic"
    assert result["summary"]["fail"] == 0

    connection = duckdb.connect(str(metric_config.database_path), read_only=True)
    try:
        day_zero = connection.execute(
            """
            SELECT daily_active_visitors, first_observed_visitors,
                   purchasing_visitors, rolling_30d_active_visitors
            FROM mart.daily_activity ORDER BY activity_date LIMIT 1
            """
        ).fetchone()
        session_funnel = dict(
            connection.execute(
                """
                SELECT metric_id, numerator_count
                FROM mart.funnel_summary
                WHERE funnel_scope = 'session'
                  AND metric_id IN ('ordered_view_to_cart_rate',
                                    'ordered_cart_to_purchase_rate')
                """
            ).fetchall()
        )
        d7_segments = {
            segment: (eligible, retained, rate)
            for segment, eligible, retained, rate in connection.execute(
                """
                SELECT first_session_segment, eligible_visitor_count,
                       retained_visitor_count, weighted_retention_rate
                FROM mart.retention_summary
                WHERE day_n = 7
                  AND first_session_segment IN ('cart_no_purchase', 'browse_only')
                """
            ).fetchall()
        }
        censored = connection.execute(
            """
            SELECT is_eligible, retained_visitors, retention_rate
            FROM mart.retention_cohort_daily
            WHERE cohort_date = DATE '2015-06-29'
              AND first_session_segment = 'browse_only'
              AND day_n = 7
            """
        ).fetchone()
        transactions = connection.execute(
            """
            SELECT active_visitor_count, purchasing_visitor_count,
                   repeat_purchase_visitor_count, transaction_count,
                   transaction_event_count, repeat_purchase_visitor_rate
            FROM mart.transaction_summary
            """
        ).fetchone()
        hypotheses = connection.execute(
            """
            SELECT hypothesis_id, is_supported, observed_effect
            FROM mart.hypothesis_results ORDER BY hypothesis_id
            """
        ).fetchall()
    finally:
        connection.close()

    assert day_zero == (5, 5, 2, 5)
    assert session_funnel == {
        "ordered_view_to_cart_rate": 3,
        "ordered_cart_to_purchase_rate": 2,
    }
    assert d7_segments["cart_no_purchase"] == (1, 1, 1.0)
    assert d7_segments["browse_only"] == (2, 0, 0.0)
    assert censored == (False, None, None)
    assert transactions == (7, 2, 1, 3, 4, 0.5)
    assert hypotheses[0][0] == "H1"
    assert hypotheses[0][1] is True
    assert hypotheses[0][2] == pytest.approx(1.0)
    assert {row[0] for row in hypotheses} == {"H1", "H2", "H3"}


def test_metrics_and_exports_are_idempotent_and_aggregate_only(
    metric_config: ProjectConfig,
) -> None:
    calculate_metrics(metric_config)
    second_metrics = calculate_metrics(metric_config)
    first_export = export_metrics(metric_config)
    second_export = export_metrics(metric_config)

    assert {step["status"] for step in second_metrics["steps"]} == {"skipped"}
    assert first_export["contains_visitor_level_exports"] is False
    assert second_export["status"] == "success"

    export_directory = Path(second_export["export_directory"])
    manifest = json.loads((export_directory / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["files"]) == 2 * len(EXPORT_RELATIONS)
    assert manifest["contains_visitor_level_exports"] is False
    assert all("visitor_daily_activity" not in item["path"] for item in manifest["files"])
    assert all(Path(item["path"]).is_file() for item in manifest["files"])
    assert (export_directory / "metrics_summary.md").is_file()


def test_run_all_executes_the_complete_v03_pipeline(tmp_path: Path) -> None:
    config = _fixture_config(tmp_path)

    result = run_all(config)

    assert result["milestone"] == "v0.3.0"
    assert result["status"] == "success"
    assert tuple(result["steps"]) == ("ingest", "build", "metrics", "validate", "export")
    assert result["steps"]["metrics"]["summary"]["fail"] == 0
    assert result["steps"]["validate"]["summary"]["fail"] == 0
