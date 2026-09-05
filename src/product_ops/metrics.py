"""Versioned Goal 3 metric builds, validation, hypothesis tests, and exports."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path
from typing import Any

from product_ops.config import ProjectConfig
from product_ops.sql_runner import load_sql, sql_literal
from product_ops.warehouse import (
    WarehouseError,
    _connect,
    _execute_build_steps,
    _git_revision,
    _manifest_input_hash,
    _prepare_storage,
    _record_failure_if_possible,
    _record_run_finish,
    _record_run_start,
    _relation_exists,
    _require_table,
    _runtime_paths,
    _store_quality_checks,
    _utc_now,
)

METRIC_SQL_FILES = (
    "mart/001_registry_activity.sql",
    "mart/002_funnel_paths.sql",
    "mart/003_retention.sql",
    "mart/004_transactions_lifecycle.sql",
    "mart/005_product_category_quality.sql",
    "mart/006_hypotheses.sql",
)

METRIC_RELATIONS = (
    "mart.metric_registry",
    "mart.visitor_daily_activity",
    "mart.session_metrics",
    "mart.daily_activity",
    "mart.daily_session_metrics",
    "mart.session_funnel",
    "mart.session_item_funnel",
    "mart.funnel_summary",
    "mart.funnel_latency_summary",
    "mart.session_path_summary",
    "mart.funnel_anomaly_summary",
    "mart.visitor_cohort",
    "mart.retention_cohort_daily",
    "mart.retention_summary",
    "mart.retention_cohort_weekly",
    "mart.transaction_metrics",
    "mart.visitor_transaction_summary",
    "mart.visitor_repurchase_interval",
    "mart.transaction_daily",
    "mart.transaction_summary",
    "mart.lifecycle_threshold",
    "mart.visitor_lifecycle",
    "mart.lifecycle_segment_summary",
    "mart.item_performance",
    "mart.category_session_funnel",
    "mart.category_performance",
    "mart.data_quality_summary",
    "mart.hypothesis_results",
)

EXPORT_RELATIONS = (
    "mart.metric_registry",
    "mart.daily_activity",
    "mart.daily_session_metrics",
    "mart.funnel_summary",
    "mart.funnel_latency_summary",
    "mart.session_path_summary",
    "mart.funnel_anomaly_summary",
    "mart.retention_cohort_daily",
    "mart.retention_summary",
    "mart.retention_cohort_weekly",
    "mart.transaction_daily",
    "mart.transaction_summary",
    "mart.lifecycle_segment_summary",
    "mart.item_performance",
    "mart.category_performance",
    "mart.data_quality_summary",
    "mart.hypothesis_results",
)


class MetricsError(WarehouseError):
    """Raised when metric calculation or export cannot safely complete."""


def calculate_metrics(config: ProjectConfig) -> dict[str, Any]:
    """Build all versioned metric marts and run blocking metric checks."""

    paths = _runtime_paths(config)
    _prepare_storage(paths, demo_mode=config.demo_mode)
    run_id = str(uuid.uuid4())
    started_at = _utc_now()
    connection = _connect(config)
    failed: list[dict[str, Any]] = []
    try:
        connection.execute(load_sql("meta/001_initialize.sql"))
        _require_table(connection, "core.fct_event", hint="Run `product-ops build` first.")
        _require_table(
            connection,
            "core.fct_event_item_context",
            hint="Run `product-ops build` first.",
        )
        input_hash = _metric_input_hash(connection, config)
        _record_run_start(
            connection,
            run_id=run_id,
            command="metrics",
            started_at=started_at,
            code_version=_git_revision(),
            input_hash=input_hash,
        )
        steps = _execute_build_steps(
            connection,
            pipeline_run_id=run_id,
            input_hash=input_hash,
            session_gap_milliseconds=config.session_gap_minutes * 60 * 1_000,
            sql_files=METRIC_SQL_FILES,
            signature_namespace="metrics-v0.3.0",
        )
        _enrich_h1_statistics(connection)
        checks = _run_metric_quality_checks(connection)
        _store_quality_checks(connection, run_id, checks)
        failed = [check for check in checks if check["status"] == "fail"]
        _record_run_finish(
            connection,
            run_id,
            status="failed" if failed else "success",
            error_summary=(
                f"{len(failed)} blocking metric quality check(s) failed" if failed else None
            ),
        )
        relation_counts = _metric_relation_counts(connection)
        data_origin = connection.execute(
            "SELECT min(data_origin) FROM mart.metric_registry"
        ).fetchone()[0]
    except Exception as exc:
        _record_failure_if_possible(connection, run_id, exc)
        if isinstance(exc, MetricsError):
            raise
        raise MetricsError(f"Metric calculation failed: {exc}") from exc
    finally:
        connection.close()

    report = {
        "milestone": "v0.3.0",
        "command": "metrics",
        "status": "failed" if failed else "success",
        "run_id": run_id,
        "database_path": str(paths["database_path"]),
        "data_origin": data_origin,
        "generated_at_utc": _utc_now(),
        "relation_row_counts": relation_counts,
        "steps": steps,
        "summary": {
            "pass": sum(check["status"] == "pass" for check in checks),
            "warn": sum(check["status"] == "warn" for check in checks),
            "fail": len(failed),
        },
        "checks": checks,
    }
    report_path = paths["export_directory"] / "v0.3.0" / "metrics_quality_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report["report_path"] = str(report_path)
    return report


def export_metrics(config: ProjectConfig) -> dict[str, Any]:
    """Export privacy-safe aggregate marts to CSV, Parquet, JSON, and Markdown."""

    paths = _runtime_paths(config)
    _prepare_storage(paths, demo_mode=config.demo_mode)
    run_id = str(uuid.uuid4())
    started_at = _utc_now()
    export_root = paths["export_directory"] / "v0.3.0"
    temporary_root = export_root / f".tmp-{run_id}"
    connection = _connect(config)
    try:
        connection.execute(load_sql("meta/001_initialize.sql"))
        _require_table(
            connection,
            "mart.metric_registry",
            hint="Run `product-ops metrics` first.",
        )
        _record_run_start(
            connection,
            run_id=run_id,
            command="export",
            started_at=started_at,
            code_version=_git_revision(),
            input_hash=_metric_input_hash(connection, config),
        )
        export_root.mkdir(parents=True, exist_ok=True)
        temporary_root.mkdir(parents=True, exist_ok=False)
        exported = _export_relations(connection, temporary_root, export_root)
        manifest = {
            "milestone": "v0.3.0",
            "run_id": run_id,
            "generated_at_utc": _utc_now(),
            "data_origin": connection.execute(
                "SELECT min(data_origin) FROM mart.metric_registry"
            ).fetchone()[0],
            "contains_visitor_level_exports": False,
            "files": exported,
        }
        manifest_path = export_root / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        summary_path = export_root / "metrics_summary.md"
        summary_path.write_text(_render_markdown_summary(connection), encoding="utf-8")
        _record_run_finish(connection, run_id, status="success")
    except Exception as exc:
        _record_failure_if_possible(connection, run_id, exc)
        raise MetricsError(f"Metric export failed: {exc}") from exc
    finally:
        connection.close()
        if temporary_root.exists():
            shutil.rmtree(temporary_root)

    return {
        "milestone": "v0.3.0",
        "command": "export",
        "status": "success",
        "run_id": run_id,
        "database_path": str(paths["database_path"]),
        "export_directory": str(export_root),
        "manifest_path": str(manifest_path),
        "summary_path": str(summary_path),
        "exported_relation_count": len(EXPORT_RELATIONS),
        "contains_visitor_level_exports": False,
    }


def _metric_input_hash(connection: Any, config: ProjectConfig) -> str:
    digest = hashlib.sha256()
    digest.update(f"manifest:{_manifest_input_hash(connection) or 'unknown'}\n".encode())
    digest.update(f"session_gap_minutes:{config.session_gap_minutes}\n".encode())
    core_sql = load_sql(
        "core/001_build_core.sql",
        session_gap_milliseconds=config.session_gap_minutes * 60 * 1_000,
    )
    digest.update(f"core_sql:{hashlib.sha256(core_sql.encode()).hexdigest()}\n".encode())
    for relation in ("core.fct_event", "core.fct_session", "core.fct_transaction"):
        row_count = connection.execute(f"SELECT count(*) FROM {relation}").fetchone()[0]
        digest.update(f"{relation}:{row_count}\n".encode())
    return digest.hexdigest()


def _metric_relation_counts(connection: Any) -> dict[str, int]:
    return {
        relation: connection.execute(f"SELECT count(*) FROM {relation}").fetchone()[0]
        for relation in METRIC_RELATIONS
    }


def _run_metric_quality_checks(connection: Any) -> list[dict[str, Any]]:
    definitions = (
        (
            "metric_registry_populated",
            "blocking",
            "SELECT count(*) FROM mart.metric_registry",
            0,
            "greater",
            "指标注册表已生成",
        ),
        (
            "daily_activity_populated",
            "blocking",
            "SELECT count(*) FROM mart.daily_activity",
            0,
            "greater",
            "日活指标已生成",
        ),
        (
            "daily_activity_bounds",
            "blocking",
            """
            SELECT count(*) FROM mart.daily_activity
            WHERE daily_active_visitors > rolling_7d_active_visitors
               OR rolling_7d_active_visitors > rolling_30d_active_visitors
               OR dau_mau_stickiness NOT BETWEEN 0 AND 1
               OR purchasing_visitor_rate NOT BETWEEN 0 AND 1
            """,
            0,
            "equal",
            "活跃指标满足人数和比率边界",
        ),
        (
            "funnel_numerator_not_above_denominator",
            "blocking",
            """
            SELECT count(*) FROM mart.funnel_summary
            WHERE numerator_count > denominator_count
               OR metric_rate NOT BETWEEN 0 AND 1
            """,
            0,
            "equal",
            "漏斗分子不超过分母",
        ),
        (
            "retention_right_censoring",
            "blocking",
            """
            SELECT count(*) FROM mart.retention_cohort_daily
            WHERE NOT is_eligible
              AND (retained_visitors IS NOT NULL OR retention_rate IS NOT NULL)
            """,
            0,
            "equal",
            "观察期不足的留存 Cohort 不计为流失",
        ),
        (
            "retention_rate_bounds",
            "blocking",
            """
            SELECT count(*) FROM mart.retention_cohort_daily
            WHERE is_eligible
              AND (retention_rate NOT BETWEEN 0 AND 1
                   OR retained_visitors > cohort_size)
            """,
            0,
            "equal",
            "可观察留存率和人数满足边界",
        ),
        (
            "transaction_count_uses_unique_ids",
            "blocking",
            """
            SELECT abs(
                (SELECT transaction_count FROM mart.transaction_summary)
                - (
                    SELECT count(*)
                    FROM (
                        SELECT transactionid
                        FROM core.fct_event
                        WHERE event = 'transaction'
                          AND transactionid IS NOT NULL
                          AND NOT is_exact_duplicate
                          AND NOT is_unknown_event
                          AND NOT has_required_null
                          AND NOT has_transaction_id_mismatch
                        GROUP BY transactionid
                        HAVING count(DISTINCT visitorid) = 1
                    ) AS eligible_transaction
                )
            )
            """,
            0,
            "equal",
            "交易数与唯一 transactionid 模型一致",
        ),
        (
            "lifecycle_visitor_coverage",
            "blocking",
            """
            SELECT abs(
                (SELECT count(*) FROM mart.visitor_lifecycle)
                - (SELECT count(*) FROM mart.visitor_cohort)
            )
            """,
            0,
            "equal",
            "每位合格访客恰有一个主生命周期分群",
        ),
        (
            "category_rate_and_wilson_bounds",
            "blocking",
            """
            SELECT count(*) FROM mart.category_performance
            WHERE session_conversion_rate NOT BETWEEN 0 AND 1
               OR conversion_wilson_low_95 > session_conversion_rate
               OR conversion_wilson_high_95 < session_conversion_rate
               OR conversion_wilson_low_95 < 0
               OR conversion_wilson_high_95 > 1
            """,
            0,
            "equal",
            "品类转化率和 Wilson 区间满足边界",
        ),
        (
            "pre_registered_hypothesis_count",
            "blocking",
            "SELECT count(*) FROM mart.hypothesis_results",
            3,
            "equal",
            "三项预登记假设均输出结果",
        ),
        (
            "metric_data_origin_valid",
            "blocking",
            """
            SELECT count(*) FROM mart.metric_registry
            WHERE data_origin NOT IN ('real', 'synthetic')
            """,
            0,
            "equal",
            "指标明确标记真实或模拟来源",
        ),
    )
    checks: list[dict[str, Any]] = []
    for check_id, severity, sql, expected, rule, description in definitions:
        actual = connection.execute(sql).fetchone()[0]
        passed = actual == expected if rule == "equal" else actual > expected
        checks.append(
            {
                "check_id": check_id,
                "severity": severity,
                "status": "pass" if passed else "fail",
                "actual_value": actual,
                "expected_value": expected if rule == "equal" else f"> {expected}",
                "description_cn": description,
            }
        )
    return checks


def _enrich_h1_statistics(connection: Any) -> None:
    row = connection.execute(
        """
        SELECT primary_success_count, primary_group_count,
               comparison_success_count, comparison_group_count
        FROM mart.hypothesis_results
        WHERE hypothesis_id = 'H1'
        """
    ).fetchone()
    if row is None or any(value is None for value in row):
        return
    primary_success, primary_total, comparison_success, comparison_total = map(int, row)
    if primary_total <= 0 or comparison_total <= 0:
        return
    primary_rate = primary_success / primary_total
    comparison_rate = comparison_success / comparison_total
    difference = primary_rate - comparison_rate
    unpooled_se = math.sqrt(
        primary_rate * (1 - primary_rate) / primary_total
        + comparison_rate * (1 - comparison_rate) / comparison_total
    )
    pooled_rate = (primary_success + comparison_success) / (primary_total + comparison_total)
    pooled_se = math.sqrt(
        pooled_rate
        * (1 - pooled_rate)
        * (1 / primary_total + 1 / comparison_total)
    )
    z_score = difference / pooled_se if pooled_se else 0.0
    p_value = math.erfc(abs(z_score) / math.sqrt(2)) if pooled_se else 1.0
    z_95 = 1.959963984540054
    confidence_low = max(-1.0, difference - z_95 * unpooled_se)
    confidence_high = min(1.0, difference + z_95 * unpooled_se)
    connection.execute(
        """
        UPDATE mart.hypothesis_results
        SET confidence_low_95 = ?, confidence_high_95 = ?, p_value = ?
        WHERE hypothesis_id = 'H1'
        """,
        [confidence_low, confidence_high, p_value],
    )


def _export_relations(
    connection: Any,
    temporary_root: Path,
    export_root: Path,
) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    for relation in EXPORT_RELATIONS:
        if not _relation_exists(connection, relation):
            raise MetricsError(f"Required export relation does not exist: {relation}")
        file_stem = relation.replace(".", "__")
        temporary_csv = temporary_root / f"{file_stem}.csv"
        temporary_parquet = temporary_root / f"{file_stem}.parquet"
        connection.execute(
            f"COPY (SELECT * FROM {relation}) TO {sql_literal(temporary_csv)} "
            "(FORMAT CSV, HEADER TRUE)"
        )
        connection.execute(
            f"COPY (SELECT * FROM {relation}) TO {sql_literal(temporary_parquet)} "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        row_count = connection.execute(f"SELECT count(*) FROM {relation}").fetchone()[0]
        for temporary_path in (temporary_csv, temporary_parquet):
            final_path = export_root / temporary_path.name
            temporary_path.replace(final_path)
            exported.append(
                {
                    "relation": relation,
                    "format": final_path.suffix.lstrip("."),
                    "path": str(final_path),
                    "byte_size": final_path.stat().st_size,
                    "sha256": _hash_file(final_path),
                    "row_count": row_count,
                }
            )
    return exported


def _render_markdown_summary(connection: Any) -> str:
    activity = connection.execute(
        """
        SELECT min(activity_date), max(activity_date),
               sum(daily_active_visitors), max(rolling_30d_active_visitors)
        FROM mart.daily_activity
        """
    ).fetchone()
    transaction = connection.execute("SELECT * FROM mart.transaction_summary").fetchone()
    transaction_columns = [item[0] for item in connection.description]
    transaction_values = dict(zip(transaction_columns, transaction, strict=True))
    hypotheses = connection.execute(
        """
        SELECT hypothesis_id, observed_effect, threshold, is_supported, evidence_summary
        FROM mart.hypothesis_results ORDER BY hypothesis_id
        """
    ).fetchall()
    lines = [
        "# v0.3.0 自动运营指标摘要",
        "",
        "> 数据来源由导出清单中的 `data_origin` 标记；完整原始数据不随导出分发。",
        "",
        "## 覆盖范围",
        "",
        f"- UTC 日期：{activity[0]} 至 {activity[1]}",
        f"- 日活访客人次合计：{activity[2]:,}",
        f"- 滚动 30 日活跃峰值：{activity[3]:,}",
        f"- 唯一交易：{transaction_values['transaction_count']:,}",
        f"- 购买访客率：{transaction_values['purchasing_visitor_rate']:.4%}",
        f"- 复购访客率：{transaction_values['repeat_purchase_visitor_rate']:.4%}",
        "",
        "## 预登记假设",
        "",
    ]
    for hypothesis_id, effect, threshold, supported, evidence in hypotheses:
        effect_text = "不可计算" if effect is None else f"{effect:.4f}"
        verdict = "支持" if supported else "不支持"
        lines.append(
            f"- **{hypothesis_id}：{verdict}**；观测效应 {effect_text}，"
            f"阈值 {threshold:.4f}。{evidence}"
        )
    lines.extend(
        [
            "",
            "## 解释边界",
            "",
            "- 首次观察不等于注册，活跃留存不等于付费留存。",
            "- 交易数使用唯一 `transactionid`，不等于交易事件行数。",
            "- 品类机会分是理论排序指标，不代表可实现新增交易。",
            "- Retailrocket 不含价格、GMV、渠道、成本或实验分组。",
            "",
        ]
    )
    return "\n".join(lines)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
