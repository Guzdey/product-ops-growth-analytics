"""DuckDB ingestion, warehouse builds, and Goal 2 quality validation."""

from __future__ import annotations

import contextlib
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from product_ops.config import ProjectConfig
from product_ops.sql_runner import load_sql, sql_literal

EXPECTED_EVENT_ROWS = 2_756_101
EXPECTED_ITEM_PROPERTY_ROWS = 20_275_902
EXPECTED_CATEGORY_ROWS = 1_669
MINIMUM_FULL_BUILD_FREE_BYTES = 5 * 1024**3


class WarehouseError(RuntimeError):
    """Raised when a warehouse command cannot safely complete."""


@dataclass(frozen=True, slots=True)
class SourceFile:
    """Validated source-file metadata before ingestion."""

    source_id: str
    path: Path
    expected_header: tuple[str, ...]
    byte_size: int
    modified_at_utc: str
    sha256: str


SOURCE_CONTRACTS = (
    ("events", "events.csv", ("timestamp", "visitorid", "event", "itemid", "transactionid")),
    (
        "item_properties_part1",
        "item_properties_part1.csv",
        ("timestamp", "itemid", "property", "value"),
    ),
    (
        "item_properties_part2",
        "item_properties_part2.csv",
        ("timestamp", "itemid", "property", "value"),
    ),
    ("category_tree", "category_tree.csv", ("categoryid", "parentid")),
)

BUILD_SQL_FILES = (
    "stg/001_stage_sources.sql",
    "core/001_build_core.sql",
)

_CREATE_TABLE_PATTERN = re.compile(
    r"\bCREATE\s+OR\s+REPLACE\s+TABLE\s+([a-z_][\w]*\.[a-z_][\w]*)",
    flags=re.IGNORECASE,
)
_DROP_TABLE_PATTERN = re.compile(
    r"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?([a-z_][\w]*\.[a-z_][\w]*)",
    flags=re.IGNORECASE,
)


def ingest(config: ProjectConfig) -> dict[str, Any]:
    """Validate and import all four CSV files with explicit DuckDB types."""

    paths = _runtime_paths(config)
    _prepare_storage(paths, demo_mode=config.demo_mode)
    sources = inspect_sources(config)
    run_id = str(uuid.uuid4())
    code_version = _git_revision()
    started_at = _utc_now()
    connection = _connect(config)
    try:
        connection.execute(load_sql("meta/001_initialize.sql"))
        _record_run_start(
            connection,
            run_id=run_id,
            command="ingest",
            started_at=started_at,
            code_version=code_version,
            input_hash=_combined_hash(sources),
        )
        rendered = load_sql(
            "raw/001_ingest.sql",
            events_csv=sql_literal(_source_path(sources, "events")),
            properties_part1_csv=sql_literal(_source_path(sources, "item_properties_part1")),
            properties_part2_csv=sql_literal(_source_path(sources, "item_properties_part2")),
            category_tree_csv=sql_literal(_source_path(sources, "category_tree")),
        )
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute(rendered)
            row_counts = _raw_row_counts(connection)
            _replace_source_manifest(
                connection,
                sources=sources,
                row_counts=row_counts,
                run_id=run_id,
                code_version=code_version,
                demo_mode=config.demo_mode,
            )
            _assert_contract_counts(row_counts, demo_mode=config.demo_mode)
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        _record_run_finish(connection, run_id, status="success")
    except Exception as exc:
        _record_failure_if_possible(connection, run_id, exc)
        raise WarehouseError(f"Ingestion failed: {exc}") from exc
    finally:
        connection.close()

    return {
        "milestone": "v0.2.0",
        "command": "ingest",
        "status": "success",
        "run_id": run_id,
        "database_path": str(paths["database_path"]),
        "row_counts": row_counts,
        "source_files": [
            {
                "source_id": source.source_id,
                "byte_size": source.byte_size,
                "sha256": source.sha256,
            }
            for source in sources
        ],
    }


def build(config: ProjectConfig) -> dict[str, Any]:
    """Build typed staging and reusable core models from the raw layer."""

    paths = _runtime_paths(config)
    _prepare_storage(paths, demo_mode=config.demo_mode)
    run_id = str(uuid.uuid4())
    connection = _connect(config)
    started_at = _utc_now()
    try:
        connection.execute(load_sql("meta/001_initialize.sql"))
        _require_table(connection, "raw.events", hint="Run `product-ops ingest` first.")
        _record_run_start(
            connection,
            run_id=run_id,
            command="build",
            started_at=started_at,
            code_version=_git_revision(),
            input_hash=_manifest_input_hash(connection),
        )
        steps = _execute_build_steps(
            connection,
            pipeline_run_id=run_id,
            input_hash=_manifest_input_hash(connection),
            session_gap_milliseconds=config.session_gap_minutes * 60 * 1_000,
        )
        model_counts = _model_row_counts(connection)
        _record_run_finish(connection, run_id, status="success")
    except Exception as exc:
        _record_failure_if_possible(connection, run_id, exc)
        raise WarehouseError(f"Warehouse build failed: {exc}") from exc
    finally:
        connection.close()

    return {
        "milestone": "v0.2.0",
        "command": "build",
        "status": "success",
        "run_id": run_id,
        "database_path": str(paths["database_path"]),
        "model_row_counts": model_counts,
        "steps": steps,
    }


def validate(config: ProjectConfig) -> dict[str, Any]:
    """Run data-contract, relationship, temporal, and model checks."""

    paths = _runtime_paths(config)
    _prepare_storage(paths, demo_mode=config.demo_mode)
    run_id = str(uuid.uuid4())
    connection = _connect(config)
    started_at = _utc_now()
    try:
        connection.execute(load_sql("meta/001_initialize.sql"))
        _require_table(connection, "core.fct_event", hint="Run ingest and build first.")
        _record_run_start(
            connection,
            run_id=run_id,
            command="validate",
            started_at=started_at,
            code_version=_git_revision(),
            input_hash=_manifest_input_hash(connection),
        )
        checks = _run_quality_checks(connection, demo_mode=config.demo_mode)
        _store_quality_checks(connection, run_id, checks)
        failed = [check for check in checks if check["status"] == "fail"]
        _record_run_finish(
            connection,
            run_id,
            status="failed" if failed else "success",
            error_summary=(f"{len(failed)} blocking quality check(s) failed" if failed else None),
        )
    except Exception as exc:
        _record_failure_if_possible(connection, run_id, exc)
        raise WarehouseError(f"Validation failed to run: {exc}") from exc
    finally:
        connection.close()

    report = {
        "milestone": "v0.2.0",
        "command": "validate",
        "status": "failed" if failed else "success",
        "run_id": run_id,
        "database_path": str(paths["database_path"]),
        "generated_at_utc": _utc_now(),
        "summary": {
            "pass": sum(check["status"] == "pass" for check in checks),
            "warn": sum(check["status"] == "warn" for check in checks),
            "fail": len(failed),
        },
        "checks": checks,
    }
    report_path = paths["export_directory"] / "v0.2.0" / "quality_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report["report_path"] = str(report_path)
    return report


def run_all(config: ProjectConfig) -> dict[str, Any]:
    """Rebuild Goal 2 from the official CSV files and validate the result."""

    ingest_result = ingest(config)
    build_result = build(config)
    validation_result = validate(config)
    return {
        "milestone": "v0.2.0",
        "command": "run-all",
        "status": validation_result["status"],
        "steps": {
            "ingest": ingest_result,
            "build": build_result,
            "validate": validation_result,
        },
    }


def inspect_sources(config: ProjectConfig) -> list[SourceFile]:
    """Validate source names and headers, then calculate immutable metadata."""

    raw_dir = _runtime_path(config.raw_data_dir)
    sources: list[SourceFile] = []
    for source_id, filename, expected_header in SOURCE_CONTRACTS:
        path = raw_dir / filename
        if not path.is_file():
            raise WarehouseError(f"Required source file is missing: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            actual_header = tuple(next(csv.reader(handle), ()))
        if actual_header != expected_header:
            raise WarehouseError(
                f"Header mismatch for {filename}: expected {expected_header}, found {actual_header}"
            )
        stat = path.stat()
        sources.append(
            SourceFile(
                source_id=source_id,
                path=path,
                expected_header=expected_header,
                byte_size=stat.st_size,
                modified_at_utc=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                sha256=_sha256(path),
            )
        )
    return sources


def _connect(config: ProjectConfig):
    try:
        import duckdb
    except ImportError as exc:
        raise WarehouseError(
            "DuckDB is not installed; install the project runtime requirements first."
        ) from exc

    paths = _runtime_paths(config)
    connection = duckdb.connect(str(paths["database_path"]))
    connection.execute(f"SET temp_directory = {sql_literal(paths['temp_directory'])}")
    connection.execute("SET threads = 4")
    connection.execute("SET memory_limit = '4GB'")
    connection.execute("SET preserve_insertion_order = true")
    return connection


def _runtime_paths(config: ProjectConfig) -> dict[str, Path]:
    return {
        "data_home": _runtime_path(config.data_home),
        "raw_data_dir": _runtime_path(config.raw_data_dir),
        "warehouse_directory": _runtime_path(config.warehouse_directory),
        "database_path": _runtime_path(config.database_path),
        "parquet_directory": _runtime_path(config.parquet_directory),
        "temp_directory": _runtime_path(config.temp_directory),
        "export_directory": _runtime_path(config.export_directory),
    }


def _runtime_path(path: os.PathLike[str]) -> Path:
    return Path(str(path))


def _prepare_storage(paths: dict[str, Path], *, demo_mode: bool) -> None:
    data_home = paths["data_home"]
    if not demo_mode and data_home.exists():
        free_bytes = shutil.disk_usage(data_home).free
        if free_bytes < MINIMUM_FULL_BUILD_FREE_BYTES:
            raise WarehouseError(
                "Full warehouse build requires at least 5 GiB free under data_home; "
                f"only {free_bytes / 1024**3:.2f} GiB is available."
            )
    for key in (
        "warehouse_directory",
        "parquet_directory",
        "temp_directory",
        "export_directory",
    ):
        paths[key].mkdir(parents=True, exist_ok=True)


def _source_path(sources: list[SourceFile], source_id: str) -> Path:
    return next(source.path for source in sources if source.source_id == source_id)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _combined_hash(sources: list[SourceFile]) -> str:
    digest = hashlib.sha256()
    for source in sorted(sources, key=lambda item: item.source_id):
        digest.update(f"{source.source_id}:{source.sha256}\n".encode())
    return digest.hexdigest()


def _raw_row_counts(connection: Any) -> dict[str, int]:
    return {
        "raw.events": connection.execute("SELECT count(*) FROM raw.events").fetchone()[0],
        "raw.item_properties": connection.execute(
            "SELECT count(*) FROM raw.item_properties"
        ).fetchone()[0],
        "raw.category_tree": connection.execute(
            "SELECT count(*) FROM raw.category_tree"
        ).fetchone()[0],
        "item_properties_part1": connection.execute(
            "SELECT count(*) FROM raw.item_properties WHERE source_id = 'item_properties_part1'"
        ).fetchone()[0],
        "item_properties_part2": connection.execute(
            "SELECT count(*) FROM raw.item_properties WHERE source_id = 'item_properties_part2'"
        ).fetchone()[0],
    }


def _assert_contract_counts(row_counts: dict[str, int], *, demo_mode: bool) -> None:
    if demo_mode:
        return
    expected = {
        "raw.events": EXPECTED_EVENT_ROWS,
        "raw.item_properties": EXPECTED_ITEM_PROPERTY_ROWS,
        "raw.category_tree": EXPECTED_CATEGORY_ROWS,
    }
    mismatches = [
        f"{name}: expected {expected_count:,}, found {row_counts[name]:,}"
        for name, expected_count in expected.items()
        if row_counts[name] != expected_count
    ]
    if mismatches:
        raise WarehouseError("Source row-count contract mismatch: " + "; ".join(mismatches))


def _replace_source_manifest(
    connection: Any,
    *,
    sources: list[SourceFile],
    row_counts: dict[str, int],
    run_id: str,
    code_version: str,
    demo_mode: bool,
) -> None:
    connection.execute("DELETE FROM meta.source_file_manifest")
    actual_by_source = {
        "events": row_counts["raw.events"],
        "item_properties_part1": row_counts["item_properties_part1"],
        "item_properties_part2": row_counts["item_properties_part2"],
        "category_tree": row_counts["raw.category_tree"],
    }
    expected_by_source = {
        "events": None if demo_mode else EXPECTED_EVENT_ROWS,
        "item_properties_part1": None,
        "item_properties_part2": None,
        "category_tree": None if demo_mode else EXPECTED_CATEGORY_ROWS,
    }
    rows = []
    for source in sources:
        rows.append(
            (
                source.source_id,
                str(source.path),
                source.path.name,
                source.byte_size,
                source.sha256,
                source.modified_at_utc,
                expected_by_source[source.source_id],
                actual_by_source[source.source_id],
                run_id,
                _utc_now(),
                code_version,
                "synthetic" if demo_mode else "retailrocket",
            )
        )
    connection.executemany(
        """
        INSERT INTO meta.source_file_manifest VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _model_row_counts(connection: Any) -> dict[str, int]:
    names = (
        "stg.events",
        "stg.item_properties",
        "stg.category_tree",
        "core.fct_event",
        "core.fct_session",
        "core.fct_transaction",
        "core.item_property_history",
        "core.item_category_history",
        "core.item_availability_history",
        "core.fct_event_item_context",
        "core.dim_category",
    )
    return {
        name: connection.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in names
    }


def _execute_build_steps(
    connection: Any,
    *,
    pipeline_run_id: str,
    input_hash: str | None,
    session_gap_milliseconds: int,
) -> list[dict[str, Any]]:
    """Execute each parsed SQL statement in its own resumable transaction."""

    cumulative_signature = hashlib.sha256(
        f"input:{input_hash or 'unknown'}\nsession_gap_ms:{session_gap_milliseconds}\n".encode()
    ).hexdigest()
    step_order = 0
    results: list[dict[str, Any]] = []
    for relative_path in BUILD_SQL_FILES:
        rendered = load_sql(
            relative_path,
            session_gap_milliseconds=session_gap_milliseconds,
        )
        for statement_number, statement in enumerate(
            connection.extract_statements(rendered), start=1
        ):
            step_order += 1
            query = statement.query.strip()
            statement_sha256 = hashlib.sha256(query.encode()).hexdigest()
            cumulative_signature = hashlib.sha256(
                f"{cumulative_signature}\n{statement_sha256}\n".encode()
            ).hexdigest()
            target_relation, operation = _statement_target(query)
            step_name = f"{relative_path}#{statement_number}:{target_relation or operation}"
            if _can_resume_step(
                connection,
                step_name=step_name,
                build_signature=cumulative_signature,
                target_relation=target_relation,
                operation=operation,
            ):
                results.append(
                    {
                        "step_name": step_name,
                        "status": "skipped",
                        "target_relation": target_relation,
                    }
                )
                continue
            result = _execute_one_build_step(
                connection,
                statement=statement,
                pipeline_run_id=pipeline_run_id,
                step_name=step_name,
                step_order=step_order,
                target_relation=target_relation,
                statement_sha256=statement_sha256,
                build_signature=cumulative_signature,
            )
            results.append(result)
    return results


def _statement_target(query: str) -> tuple[str | None, str]:
    create_match = _CREATE_TABLE_PATTERN.search(query)
    if create_match:
        return create_match.group(1).lower(), "create_table"
    drop_match = _DROP_TABLE_PATTERN.search(query)
    if drop_match:
        return drop_match.group(1).lower(), "drop_table"
    return None, "statement"


def _can_resume_step(
    connection: Any,
    *,
    step_name: str,
    build_signature: str,
    target_relation: str | None,
    operation: str,
) -> bool:
    completed = connection.execute(
        """
        SELECT count(*) FROM meta.model_build_step
        WHERE step_name = ? AND build_signature = ? AND status = 'success'
        """,
        [step_name, build_signature],
    ).fetchone()[0]
    if not completed:
        return False
    if target_relation is None:
        return True
    exists = _relation_exists(connection, target_relation)
    return not exists if operation == "drop_table" else exists


def _execute_one_build_step(
    connection: Any,
    *,
    statement: Any,
    pipeline_run_id: str,
    step_name: str,
    step_order: int,
    target_relation: str | None,
    statement_sha256: str,
    build_signature: str,
) -> dict[str, Any]:
    step_run_id = str(uuid.uuid4())
    started_at = _utc_now()
    connection.execute(
        """
        INSERT INTO meta.model_build_step
        (step_run_id, pipeline_run_id, step_name, step_order, target_relation,
         statement_sha256, build_signature, started_at_utc, finished_at_utc,
         status, row_count, error_summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 'running', NULL, NULL)
        """,
        [
            step_run_id,
            pipeline_run_id,
            step_name,
            step_order,
            target_relation,
            statement_sha256,
            build_signature,
            started_at,
        ],
    )
    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute(statement)
        connection.execute("COMMIT")
        row_count = _relation_row_count(connection, target_relation)
        connection.execute(
            """
            UPDATE meta.model_build_step
            SET finished_at_utc = ?, status = 'success', row_count = ?
            WHERE step_run_id = ?
            """,
            [_utc_now(), row_count, step_run_id],
        )
    except Exception as exc:
        with contextlib.suppress(Exception):
            connection.execute("ROLLBACK")
        connection.execute(
            """
            UPDATE meta.model_build_step
            SET finished_at_utc = ?, status = 'failed', error_summary = ?
            WHERE step_run_id = ?
            """,
            [_utc_now(), str(exc)[:1000], step_run_id],
        )
        raise
    return {
        "step_name": step_name,
        "status": "built",
        "target_relation": target_relation,
        "row_count": row_count,
    }


def _relation_exists(connection: Any, relation_name: str) -> bool:
    schema, name = relation_name.split(".", maxsplit=1)
    return bool(
        connection.execute(
            """
            SELECT count(*) FROM information_schema.tables
            WHERE table_schema = ? AND table_name = ?
            """,
            [schema, name],
        ).fetchone()[0]
    )


def _relation_row_count(connection: Any, relation_name: str | None) -> int | None:
    if relation_name is None or not _relation_exists(connection, relation_name):
        return None
    return connection.execute(f"SELECT count(*) FROM {relation_name}").fetchone()[0]


def _run_quality_checks(connection: Any, *, demo_mode: bool) -> list[dict[str, Any]]:
    event_expected = None if demo_mode else EXPECTED_EVENT_ROWS
    property_expected = None if demo_mode else EXPECTED_ITEM_PROPERTY_ROWS
    category_expected = None if demo_mode else EXPECTED_CATEGORY_ROWS
    definitions = [
        (
            "raw_event_row_count",
            "blocking",
            "SELECT count(*) FROM raw.events",
            event_expected,
            "equal" if event_expected is not None else "positive",
            "原始事件行数符合数据契约",
        ),
        (
            "raw_item_property_row_count",
            "blocking",
            "SELECT count(*) FROM raw.item_properties",
            property_expected,
            "equal" if property_expected is not None else "positive",
            "两份商品属性已完整合并",
        ),
        (
            "raw_category_row_count",
            "blocking",
            "SELECT count(*) FROM raw.category_tree",
            category_expected,
            "equal" if category_expected is not None else "positive",
            "分类树行数符合数据契约",
        ),
        (
            "core_event_row_count_matches_raw",
            "blocking",
            "SELECT (SELECT count(*) FROM core.fct_event) - (SELECT count(*) FROM raw.events)",
            0,
            "equal",
            "核心事件层没有增删原始事件",
        ),
        (
            "event_context_row_count_matches_event",
            "blocking",
            "SELECT (SELECT count(*) FROM core.fct_event_item_context) - "
            "(SELECT count(*) FROM core.fct_event)",
            0,
            "equal",
            "ASOF 商品上下文关联没有放大或丢失事件",
        ),
        (
            "future_property_leakage",
            "blocking",
            """
            SELECT count(*) FROM core.fct_event_item_context
            WHERE (category_valid_from_utc IS NOT NULL
                   AND category_valid_from_utc > event_time_utc)
               OR (available_valid_from_utc IS NOT NULL
                   AND available_valid_from_utc > event_time_utc)
            """,
            0,
            "equal",
            "事件未关联未来才出现的商品属性",
        ),
        (
            "invalid_property_intervals",
            "blocking",
            """
            SELECT count(*) FROM core.item_property_history
            WHERE valid_to_utc IS NOT NULL AND valid_to_utc <= valid_from_utc
            """,
            0,
            "equal",
            "商品属性历史满足左闭右开有效区间",
        ),
        (
            "unknown_event_rows",
            "warning",
            "SELECT count(*) FROM stg.events WHERE is_unknown_event",
            0,
            "equal",
            "未知事件类型被保留并报告",
        ),
        (
            "event_required_null_rows",
            "warning",
            "SELECT count(*) FROM stg.events WHERE has_required_null",
            0,
            "equal",
            "事件必填字段空值被报告",
        ),
        (
            "transaction_without_id_rows",
            "warning",
            "SELECT count(*) FROM stg.events WHERE event = 'transaction' AND transactionid IS NULL",
            0,
            "equal",
            "交易事件缺少 transactionid 的记录被报告",
        ),
        (
            "non_transaction_with_id_rows",
            "warning",
            "SELECT count(*) FROM stg.events "
            "WHERE event <> 'transaction' AND transactionid IS NOT NULL",
            0,
            "equal",
            "非交易事件携带 transactionid 的记录被报告",
        ),
        (
            "exact_duplicate_event_rows",
            "warning",
            "SELECT count(*) FROM stg.events WHERE is_exact_duplicate",
            0,
            "equal",
            "事件精确重复行未删除并被标记",
        ),
        (
            "item_property_conflict_rows",
            "warning",
            "SELECT count(*) FROM stg.item_properties WHERE has_timestamp_conflict",
            0,
            "equal",
            "同商品属性同时间的多值冲突被报告",
        ),
        (
            "category_cycle_nodes",
            "blocking",
            "SELECT count(*) FROM core.dim_category WHERE has_cycle",
            0,
            "equal",
            "分类树不存在环",
        ),
        (
            "category_missing_ancestor_nodes",
            "warning",
            "SELECT count(*) FROM core.dim_category WHERE has_missing_ancestor",
            0,
            "equal",
            "缺失父级或不可达分类被报告",
        ),
    ]
    checks: list[dict[str, Any]] = []
    for check_id, severity, sql, expected, rule, description in definitions:
        actual = connection.execute(sql).fetchone()[0]
        passed = actual == expected if rule == "equal" else actual > 0
        status = "pass" if passed else ("fail" if severity == "blocking" else "warn")
        checks.append(
            {
                "check_id": check_id,
                "severity": severity,
                "status": status,
                "actual_value": actual,
                "expected_value": expected if rule == "equal" else "> 0",
                "description_cn": description,
            }
        )
    return checks


def _store_quality_checks(connection: Any, run_id: str, checks: list[dict[str, Any]]) -> None:
    connection.execute("DELETE FROM meta.quality_check WHERE run_id = ?", [run_id])
    connection.executemany(
        """
        INSERT INTO meta.quality_check
        (run_id, check_id, severity, status, actual_value, expected_value,
         description_cn, checked_at_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                check["check_id"],
                check["severity"],
                check["status"],
                str(check["actual_value"]),
                str(check["expected_value"]),
                check["description_cn"],
                _utc_now(),
            )
            for check in checks
        ],
    )


def _record_run_start(
    connection: Any,
    *,
    run_id: str,
    command: str,
    started_at: str,
    code_version: str,
    input_hash: str | None,
) -> None:
    recovered_at = _utc_now()
    connection.execute(
        """
        UPDATE meta.pipeline_run
        SET finished_at_utc = ?,
            status = 'abandoned',
            error_summary = coalesce(
                error_summary,
                'Process ended before a final status was recorded; recovered by next run.'
            )
        WHERE status = 'running'
        """,
        [recovered_at],
    )
    connection.execute(
        """
        UPDATE meta.model_build_step
        SET finished_at_utc = ?,
            status = 'abandoned',
            error_summary = coalesce(
                error_summary,
                'Process ended before this SQL step committed; recovered by next run.'
            )
        WHERE status = 'running'
        """,
        [recovered_at],
    )
    connection.execute(
        """
        INSERT INTO meta.pipeline_run
        (run_id, command, started_at_utc, finished_at_utc, status,
         input_hash, code_version, error_summary)
        VALUES (?, ?, ?, NULL, 'running', ?, ?, NULL)
        """,
        [run_id, command, started_at, input_hash, code_version],
    )


def _record_run_finish(
    connection: Any,
    run_id: str,
    *,
    status: str,
    error_summary: str | None = None,
) -> None:
    connection.execute(
        """
        UPDATE meta.pipeline_run
        SET finished_at_utc = ?, status = ?, error_summary = ?
        WHERE run_id = ?
        """,
        [_utc_now(), status, error_summary, run_id],
    )


def _record_failure_if_possible(connection: Any, run_id: str, exc: Exception) -> None:
    try:
        _record_run_finish(connection, run_id, status="failed", error_summary=str(exc)[:1000])
    except Exception:
        return


def _require_table(connection: Any, table_name: str, *, hint: str) -> None:
    schema, name = table_name.split(".", maxsplit=1)
    exists = connection.execute(
        """
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema = ? AND table_name = ?
        """,
        [schema, name],
    ).fetchone()[0]
    if not exists:
        raise WarehouseError(f"Required table {table_name} does not exist. {hint}")


def _manifest_input_hash(connection: Any) -> str | None:
    rows = connection.execute(
        "SELECT source_id, sha256 FROM meta.source_file_manifest ORDER BY source_id"
    ).fetchall()
    if not rows:
        return None
    digest = hashlib.sha256()
    for source_id, source_hash in rows:
        digest.update(f"{source_id}:{source_hash}\n".encode())
    return digest.hexdigest()


def _git_revision() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()
