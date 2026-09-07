"""Data access and presentation helpers for the Streamlit dashboard.

The dashboard deliberately reads metric exports rather than the raw Retailrocket
CSVs.  SQL remains the source of truth for every metric; this module only loads,
validates, filters, and formats the already aggregated results.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_FULL_EXPORT_DIRECTORY = Path(r"D:\CodexData\product-ops-growth-analytics\exports\v0.3.0")
TABLE_FILES = {
    "daily_activity": "mart__daily_activity.csv",
    "daily_session_metrics": "mart__daily_session_metrics.csv",
    "funnel_summary": "mart__funnel_summary.csv",
    "funnel_latency_summary": "mart__funnel_latency_summary.csv",
    "session_path_summary": "mart__session_path_summary.csv",
    "funnel_anomaly_summary": "mart__funnel_anomaly_summary.csv",
    "retention_cohort_daily": "mart__retention_cohort_daily.csv",
    "retention_summary": "mart__retention_summary.csv",
    "retention_cohort_weekly": "mart__retention_cohort_weekly.csv",
    "transaction_daily": "mart__transaction_daily.csv",
    "transaction_summary": "mart__transaction_summary.csv",
    "lifecycle_segment_summary": "mart__lifecycle_segment_summary.csv",
    "item_performance": "mart__item_performance.csv",
    "category_performance": "mart__category_performance.csv",
    "data_quality_summary": "mart__data_quality_summary.csv",
    "hypothesis_results": "mart__hypothesis_results.csv",
    "metric_registry": "mart__metric_registry.csv",
}
DATE_COLUMNS = {
    "daily_activity": ("activity_date",),
    "daily_session_metrics": ("activity_date",),
    "retention_cohort_daily": ("cohort_date", "target_date"),
    "retention_cohort_weekly": ("cohort_week",),
    "transaction_daily": ("transaction_date",),
}
FORBIDDEN_DETAIL_COLUMNS = frozenset({"visitorid", "transactionid", "session_id", "session_key"})


class DashboardDataError(RuntimeError):
    """Raised when a dashboard export is missing or violates its contract."""


@dataclass(frozen=True, slots=True)
class DashboardSource:
    """Resolved dashboard input with an explicit provenance label."""

    directory: Path
    mode: str
    label: str
    manifest: dict[str, Any]


def bundled_snapshot_directory() -> Path:
    """Return the repository's small, visitor-safe real-data snapshot."""

    return Path(__file__).resolve().parents[2] / "demo_data" / "v0.4.0"


def resolve_dashboard_source(
    export_directory: str | os.PathLike[str] | None = None,
) -> DashboardSource:
    """Prefer a full local metric export and fall back to the bundled snapshot.

    ``PRODUCT_OPS_DASHBOARD_EXPORT_DIR`` can select another validated aggregate
    export.  The fallback is still real Retailrocket data, but some high-cardinality
    tables are deliberately limited for public demonstration.
    """

    explicit = export_directory or os.getenv("PRODUCT_OPS_DASHBOARD_EXPORT_DIR")
    candidates: list[tuple[Path, str, str]] = []
    if explicit:
        explicit_path = Path(explicit)
        snapshot_path = bundled_snapshot_directory()
        if explicit_path.resolve() == snapshot_path.resolve():
            candidates.append(
                (
                    explicit_path,
                    "bundled_snapshot",
                    "官方真实数据聚合快照（公开演示版）",
                )
            )
        else:
            candidates.append((explicit_path, "custom_export", "自定义聚合导出"))
    else:
        candidates.append((DEFAULT_FULL_EXPORT_DIRECTORY, "full_export", "本地全量数据聚合结果"))
        candidates.append(
            (
                bundled_snapshot_directory(),
                "bundled_snapshot",
                "官方真实数据聚合快照（公开演示版）",
            )
        )

    problems: list[str] = []
    for directory, mode, label in candidates:
        missing = [name for name in TABLE_FILES.values() if not (directory / name).is_file()]
        if missing:
            problems.append(f"{directory}: missing {', '.join(missing[:3])}")
            continue
        manifest = _load_manifest(directory)
        if manifest.get("data_origin") != "real":
            problems.append(f"{directory}: data_origin must be 'real'")
            continue
        return DashboardSource(directory, mode, label, manifest)

    details = "; ".join(problems)
    raise DashboardDataError(f"No valid dashboard aggregate export found. {details}")


def load_dashboard_tables(source: DashboardSource) -> dict[str, pd.DataFrame]:
    """Load and validate all aggregate tables required by the six dashboard pages."""

    tables: dict[str, pd.DataFrame] = {}
    for table_name, filename in TABLE_FILES.items():
        frame = pd.read_csv(source.directory / filename)
        _validate_frame(table_name, frame)
        for column in DATE_COLUMNS.get(table_name, ()):
            if column in frame:
                frame[column] = pd.to_datetime(frame[column], errors="raise").dt.date
        tables[table_name] = frame
    return tables


def filter_date_range(
    frame: pd.DataFrame,
    column: str,
    start_date: object,
    end_date: object,
) -> pd.DataFrame:
    """Return rows in an inclusive date window without mutating the input."""

    mask = (frame[column] >= start_date) & (frame[column] <= end_date)
    return frame.loc[mask].copy()


def metric_row(frame: pd.DataFrame, metric_id: str, **dimensions: object) -> pd.Series:
    """Return one named metric row after applying explicit dimension filters."""

    matches = frame.loc[frame["metric_id"] == metric_id]
    for column, value in dimensions.items():
        if column not in matches:
            raise DashboardDataError(f"Metric table lacks requested dimension {column!r}")
        matches = matches.loc[matches[column] == value]
    if len(matches) != 1:
        filters = ", ".join(f"{key}={value!r}" for key, value in dimensions.items())
        context = f" ({filters})" if filters else ""
        raise DashboardDataError(
            f"Expected one row for metric_id={metric_id!r}{context}; found {len(matches)}"
        )
    return matches.iloc[0]


def hypothesis_row(frame: pd.DataFrame, hypothesis_id: str) -> pd.Series:
    """Return exactly one pre-registered hypothesis result."""

    matches = frame.loc[frame["hypothesis_id"] == hypothesis_id]
    if len(matches) != 1:
        raise DashboardDataError(
            f"Expected one row for hypothesis_id={hypothesis_id!r}; found {len(matches)}"
        )
    return matches.iloc[0]


def _load_manifest(directory: Path) -> dict[str, Any]:
    for filename in ("dashboard_manifest.json", "manifest.json"):
        path = directory / filename
        if path.is_file():
            try:
                parsed = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise DashboardDataError(f"Cannot read dashboard manifest {path}: {exc}") from exc
            if not isinstance(parsed, dict):
                raise DashboardDataError(f"Dashboard manifest {path} must be a JSON object")
            return parsed
    raise DashboardDataError(f"No manifest found in {directory}")


def _validate_frame(table_name: str, frame: pd.DataFrame) -> None:
    if frame.empty:
        raise DashboardDataError(f"Dashboard table {table_name!r} is empty")
    forbidden = FORBIDDEN_DETAIL_COLUMNS.intersection(frame.columns)
    if forbidden:
        names = ", ".join(sorted(forbidden))
        raise DashboardDataError(
            f"Dashboard table {table_name!r} exposes visitor-level columns: {names}"
        )
    if "data_origin" not in frame.columns:
        raise DashboardDataError(f"Dashboard table {table_name!r} lacks data_origin")
    origins = set(frame["data_origin"].dropna().astype(str))
    if origins != {"real"}:
        raise DashboardDataError(
            f"Dashboard table {table_name!r} must contain only real data; found {origins}"
        )
