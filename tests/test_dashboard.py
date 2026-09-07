"""Dashboard aggregate-source contract tests that do not need full production data."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from product_ops.dashboard import (
    FORBIDDEN_DETAIL_COLUMNS,
    TABLE_FILES,
    DashboardDataError,
    bundled_snapshot_directory,
    filter_date_range,
    hypothesis_row,
    load_dashboard_tables,
    metric_row,
    resolve_dashboard_source,
)


def test_bundled_snapshot_is_real_aggregate_data_without_visitor_detail() -> None:
    source = resolve_dashboard_source(bundled_snapshot_directory())
    tables = load_dashboard_tables(source)

    assert source.manifest["data_origin"] == "real"
    assert source.manifest["contains_visitor_level_exports"] is False
    assert set(tables) == set(TABLE_FILES)
    for frame in tables.values():
        assert set(frame["data_origin"]) == {"real"}
        assert not FORBIDDEN_DETAIL_COLUMNS.intersection(frame.columns)


def test_snapshot_manifest_hashes_and_row_counts_match_files() -> None:
    source = resolve_dashboard_source(bundled_snapshot_directory())
    manifest_files = source.manifest["files"]
    tables = load_dashboard_tables(source)

    assert len(manifest_files) == len(TABLE_FILES)
    for item in manifest_files:
        path = source.directory / item["path"]
        assert path.stat().st_size == item["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        assert len(tables[item["table"]]) == item["rows"]


def test_dashboard_metrics_retain_full_sql_results() -> None:
    source = resolve_dashboard_source(bundled_snapshot_directory())
    tables = load_dashboard_tables(source)

    view_to_cart = metric_row(
        tables["funnel_summary"],
        "ordered_view_to_cart_rate",
        funnel_scope="session",
    )
    h2 = hypothesis_row(tables["hypothesis_results"], "H2")

    assert view_to_cart["numerator_count"] == 36_512
    assert view_to_cart["denominator_count"] == 1_755_714
    assert h2["is_supported"]
    assert h2["observed_effect"] > h2["threshold"]
    assert set(tables["retention_summary"]["first_session_segment"]) == {
        "all",
        "browse_only",
        "cart_no_purchase",
        "first_session_purchase",
    }


def test_date_filter_is_inclusive() -> None:
    source = resolve_dashboard_source(bundled_snapshot_directory())
    activity = load_dashboard_tables(source)["daily_activity"]
    selected = filter_date_range(
        activity,
        "activity_date",
        activity.iloc[3]["activity_date"],
        activity.iloc[5]["activity_date"],
    )

    assert len(selected) == 3
    assert selected.iloc[0]["activity_date"] == activity.iloc[3]["activity_date"]
    assert selected.iloc[-1]["activity_date"] == activity.iloc[5]["activity_date"]


def test_public_snapshot_stays_small() -> None:
    snapshot = bundled_snapshot_directory()
    total_bytes = sum(path.stat().st_size for path in Path(snapshot).glob("*"))

    assert total_bytes < 1024 * 1024


def test_invalid_explicit_dashboard_source_does_not_silently_fallback(tmp_path) -> None:
    with pytest.raises(DashboardDataError, match="No valid dashboard aggregate export"):
        resolve_dashboard_source(tmp_path / "missing-export")
