"""Deterministic end-to-end tests for the Goal 2 DuckDB warehouse."""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb

from product_ops.config import ProjectConfig
from product_ops.warehouse import build, ingest, validate


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _fixture_config(tmp_path: Path) -> ProjectConfig:
    data_home = tmp_path / "retailrocket-fixture"
    raw = data_home / "raw" / "extracted"
    minute = 60 * 1_000
    _write_csv(
        raw / "events.csv",
        ["timestamp", "visitorid", "event", "itemid", "transactionid"],
        [
            [0, 1, "view", 10, ""],
            [29 * minute, 1, "addtocart", 10, ""],
            [0, 2, "view", 10, ""],
            [30 * minute, 2, "transaction", 10, 900],
            [0, 3, "view", 20, ""],
            [31 * minute, 3, "view", 20, ""],
            [50, 4, "view", 30, ""],
            [150, 4, "view", 30, ""],
            [250, 4, "view", 30, ""],
            [300, 4, "transaction", 30, 901],
            [301, 4, "transaction", 31, 901],
        ],
    )
    _write_csv(
        raw / "item_properties_part1.csv",
        ["timestamp", "itemid", "property", "value"],
        [
            [100, 30, "categoryid", 2],
            [200, 30, "categoryid", 3],
            [100, 30, "available", 1],
            [200, 30, "available", 0],
            [100, 10, "categoryid", 2],
        ],
    )
    _write_csv(
        raw / "item_properties_part2.csv",
        ["timestamp", "itemid", "property", "value"],
        [[100, 20, "categoryid", 3], [100, 31, "categoryid", 3]],
    )
    _write_csv(
        raw / "category_tree.csv",
        ["categoryid", "parentid"],
        [[1, ""], [2, 1], [3, 1]],
    )
    return ProjectConfig.from_mapping({"data_home": str(data_home), "demo_mode": True})


def test_goal2_pipeline_builds_sessions_transactions_asof_and_categories(tmp_path) -> None:
    config = _fixture_config(tmp_path)

    ingest_result = ingest(config)
    build_result = build(config)
    validation_result = validate(config)

    assert ingest_result["row_counts"]["raw.events"] == 11
    assert build_result["model_row_counts"]["core.fct_event"] == 11
    assert validation_result["status"] == "success"

    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        session_counts = dict(
            connection.execute(
                "SELECT visitorid, count(*) FROM core.fct_session "
                "WHERE visitorid IN (1, 2, 3) GROUP BY visitorid ORDER BY visitorid"
            ).fetchall()
        )
        transaction = connection.execute(
            "SELECT transaction_event_count, distinct_item_count "
            "FROM core.fct_transaction WHERE transactionid = 901"
        ).fetchone()
        contexts = connection.execute(
            "SELECT event_timestamp_ms, categoryid, available "
            "FROM core.fct_event_item_context WHERE itemid = 30 "
            "ORDER BY event_timestamp_ms"
        ).fetchall()
        category = connection.execute(
            "SELECT root_categoryid, depth, category_path "
            "FROM core.dim_category WHERE categoryid = 3"
        ).fetchone()
    finally:
        connection.close()

    assert session_counts == {1: 1, 2: 1, 3: 2}
    assert transaction == (2, 2)
    assert contexts == [
        (50, None, None),
        (150, 2, 1),
        (250, 3, 0),
        (300, 3, 0),
    ]
    assert category == (1, 1, "/1/3/")


def test_repeated_ingest_and_build_are_idempotent(tmp_path) -> None:
    config = _fixture_config(tmp_path)

    ingest(config)
    build(config)
    ingest(config)
    second_build = build(config)

    assert second_build["model_row_counts"]["core.fct_event"] == 11
    assert second_build["model_row_counts"]["core.fct_transaction"] == 2
    assert second_build["steps"]
    assert {step["status"] for step in second_build["steps"]} == {"skipped"}
    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        assert connection.execute("SELECT count(*) FROM raw.events").fetchone()[0] == 11
        assert connection.execute("SELECT count(*) FROM core.fct_event").fetchone()[0] == 11
    finally:
        connection.close()


def test_next_run_marks_unfinished_pipeline_run_as_abandoned(tmp_path) -> None:
    config = _fixture_config(tmp_path)
    ingest(config)
    connection = duckdb.connect(str(config.database_path))
    try:
        connection.execute(
            """
            INSERT INTO meta.pipeline_run
            VALUES ('interrupted', 'build', current_timestamp, NULL,
                    'running', NULL, 'test', NULL)
            """
        )
    finally:
        connection.close()

    build(config)

    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        recovered = connection.execute(
            "SELECT status, error_summary FROM meta.pipeline_run WHERE run_id = 'interrupted'"
        ).fetchone()
    finally:
        connection.close()
    assert recovered is not None
    assert recovered[0] == "abandoned"
    assert "recovered by next run" in recovered[1]
