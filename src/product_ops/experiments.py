"""Deterministic, isolated synthetic channel and A/B experiment workflow."""

from __future__ import annotations

import hashlib
import json
import math
import random
import shutil
import uuid
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from product_ops.config import ProjectConfig
from product_ops.sql_runner import load_sql, sql_literal
from product_ops.warehouse import (
    WarehouseError,
    _connect,
    _git_revision,
    _prepare_storage,
    _record_failure_if_possible,
    _record_run_finish,
    _record_run_start,
    _runtime_paths,
    _store_quality_checks,
    _utc_now,
)

MILESTONE = "v0.5.0"
DATA_ORIGIN = "synthetic"
START_DATE = date(2026, 6, 1)
EXPERIMENT_DAYS = 28
PARTICIPANTS_PER_ARM = 10_000
REQUIRED_SAMPLE_PER_ARM = 10_000
ALPHA = 0.05
CONFIDENCE_Z = 1.959963984540054

SCENARIO_SPECS = {
    "no_effect": {
        "name_cn": "无效果场景",
        "control_clicks": 2_500,
        "variant_clicks": 2_500,
        "control_conversions": 800,
        "variant_conversions": 800,
    },
    "positive_effect": {
        "name_cn": "正向效果场景",
        "control_clicks": 2_500,
        "variant_clicks": 2_700,
        "control_conversions": 800,
        "variant_conversions": 920,
    },
}

CHANNELS = {
    "paid_search": {"weight": 35, "cpc": 1.20, "campaigns": ("SEA-A", "SEA-B")},
    "paid_social": {"weight": 30, "cpc": 0.95, "campaigns": ("SOC-A", "SOC-B")},
    "affiliate": {"weight": 20, "cpc": 0.72, "campaigns": ("AFF-A", "AFF-B")},
    "display": {"weight": 15, "cpc": 0.58, "campaigns": ("DSP-A", "DSP-B")},
}

EXPORT_RELATIONS = (
    "synthetic.metric_registry",
    "synthetic.experiment_arm_metrics",
    "synthetic.experiment_results",
    "synthetic.channel_daily_metrics",
    "synthetic.channel_summary",
    "synthetic.guardrail_summary",
)


class ExperimentError(WarehouseError):
    """Raised when the synthetic experiment workflow cannot complete safely."""


def run_experiments(config: ProjectConfig) -> dict[str, Any]:
    """Generate, calculate, test, validate, and export both synthetic scenarios."""

    paths = _runtime_paths(config)
    _prepare_storage(paths, demo_mode=config.demo_mode)
    run_id = str(uuid.uuid4())
    started_at = _utc_now()
    connection = _connect(config)
    try:
        connection.execute(load_sql("meta/001_initialize.sql"))
        _record_run_start(
            connection,
            run_id=run_id,
            command="experiment",
            started_at=started_at,
            code_version=_git_revision(),
            input_hash=_simulation_input_hash(config.synthetic_seed),
        )
        connection.execute(load_sql("synthetic/001_initialize.sql"))
        assignments = _generate_assignments(config.synthetic_seed)
        daily_inputs = _aggregate_channel_daily(assignments, config.synthetic_seed)
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.executemany(
                """
                INSERT INTO synthetic.experiment_assignment VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                assignments,
            )
            connection.executemany(
                """
                INSERT INTO synthetic.channel_daily_input VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                daily_inputs,
            )
        except Exception:
            connection.execute("ROLLBACK")
            raise
        else:
            connection.execute("COMMIT")
        connection.execute(load_sql("synthetic/002_build_metrics.sql"))
        _store_experiment_results(connection, config.synthetic_seed)
        checks = _run_quality_checks(connection, config.synthetic_seed)
        _store_quality_checks(connection, run_id, checks)
        failed = [check for check in checks if check["status"] == "fail"]
        if failed:
            raise ExperimentError(f"{len(failed)} blocking synthetic quality check(s) failed")
        export_result = _export_experiment_aggregates(
            connection,
            paths["export_directory"],
            run_id,
            config.synthetic_seed,
        )
        _record_run_finish(connection, run_id, status="success")
        results = _fetch_dicts(
            connection,
            "SELECT * FROM synthetic.experiment_results ORDER BY scenario_id",
        )
    except Exception as exc:
        _record_failure_if_possible(connection, run_id, exc)
        if isinstance(exc, ExperimentError):
            raise
        raise ExperimentError(f"Synthetic experiment workflow failed: {exc}") from exc
    finally:
        connection.close()

    return {
        "milestone": MILESTONE,
        "command": "experiment",
        "status": "success",
        "run_id": run_id,
        "database_path": str(paths["database_path"]),
        "export_directory": export_result["export_directory"],
        "data_origin": DATA_ORIGIN,
        "seed": config.synthetic_seed,
        "participant_count": len(assignments),
        "scenarios": results,
        "summary": {
            "pass": sum(check["status"] == "pass" for check in checks),
            "warn": sum(check["status"] == "warn" for check in checks),
            "fail": 0,
        },
        "checks": checks,
        "manifest_path": export_result["manifest_path"],
    }


def _generate_assignments(seed: int) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    weighted_channels = [
        channel
        for channel, values in CHANNELS.items()
        for _ in range(int(values["weight"]))
    ]

    for scenario_offset, (scenario_id, spec) in enumerate(SCENARIO_SPECS.items()):
        for group_offset, group in enumerate(("control", "variant")):
            group_seed = seed + scenario_offset * 10_000 + group_offset * 1_000
            rng = random.Random(group_seed)
            participant_numbers = list(range(PARTICIPANTS_PER_ARM))
            rng.shuffle(participant_numbers)
            click_target = int(spec[f"{group}_clicks"])
            conversion_target = int(spec[f"{group}_conversions"])
            clicked = set(participant_numbers[:click_target])
            clicked_order = participant_numbers[:click_target]
            rng.shuffle(clicked_order)
            converted = set(clicked_order[:conversion_target])
            converted_order = clicked_order[:conversion_target]
            rng.shuffle(converted_order)
            refunded = set(converted_order[: round(conversion_target * 0.05)])

            for participant_number in range(PARTICIPANTS_PER_ARM):
                participant_id = (
                    f"sim_{seed}_{scenario_id}_{group}_{participant_number:05d}"
                )
                exposure_date = START_DATE + timedelta(days=rng.randrange(EXPERIMENT_DAYS))
                channel = weighted_channels[rng.randrange(len(weighted_channels))]
                campaigns = CHANNELS[channel]["campaigns"]
                campaign_id = campaigns[rng.randrange(len(campaigns))]
                was_clicked = participant_number in clicked
                was_converted = participant_number in converted
                was_refunded = participant_number in refunded
                order_id = (
                    f"sim_order_{seed}_{scenario_id}_{group}_{participant_number:05d}"
                    if was_converted
                    else None
                )
                order_amount = round(35 + rng.random() * 145, 2) if was_converted else None
                rows.append(
                    (
                        participant_id,
                        scenario_id,
                        group,
                        exposure_date,
                        channel,
                        campaign_id,
                        True,
                        was_clicked,
                        was_converted,
                        was_refunded,
                        order_id,
                        order_amount,
                        seed,
                        DATA_ORIGIN,
                    )
                )
    return rows


def _aggregate_channel_daily(
    assignments: list[tuple[Any, ...]], seed: int
) -> list[tuple[Any, ...]]:
    aggregates: dict[tuple[str, date, str, str], dict[str, float]] = defaultdict(
        lambda: {"impressions": 0, "clicks": 0, "conversions": 0, "revenue": 0.0}
    )
    for row in assignments:
        key = (row[1], row[3], row[4], row[5])
        values = aggregates[key]
        values["impressions"] += 1
        values["clicks"] += int(row[7])
        values["conversions"] += int(row[8])
        values["revenue"] += float(row[11] or 0)

    rows: list[tuple[Any, ...]] = []
    for key in sorted(aggregates):
        scenario_id, activity_date, channel, campaign_id = key
        values = aggregates[key]
        stable_key = f"{seed}|{scenario_id}|{activity_date}|{channel}|{campaign_id}"
        noise = int(hashlib.sha256(stable_key.encode()).hexdigest()[:8], 16) % 3000 / 100
        spend = round(
            40
            + values["impressions"] * 0.04
            + values["clicks"] * float(CHANNELS[channel]["cpc"])
            + noise,
            2,
        )
        rows.append(
            (
                scenario_id,
                activity_date,
                channel,
                campaign_id,
                spend,
                int(values["impressions"]),
                int(values["clicks"]),
                int(values["conversions"]),
                round(values["revenue"], 2),
                seed,
                DATA_ORIGIN,
            )
        )
    return rows


def _store_experiment_results(connection: Any, seed: int) -> None:
    connection.execute(
        """
        CREATE OR REPLACE TABLE synthetic.experiment_results (
            scenario_id VARCHAR NOT NULL,
            scenario_name_cn VARCHAR NOT NULL,
            metric_id VARCHAR NOT NULL,
            control_rate DOUBLE NOT NULL,
            variant_rate DOUBLE NOT NULL,
            absolute_lift DOUBLE NOT NULL,
            relative_lift DOUBLE NOT NULL,
            confidence_low DOUBLE NOT NULL,
            confidence_high DOUBLE NOT NULL,
            z_statistic DOUBLE NOT NULL,
            p_value DOUBLE NOT NULL,
            alpha DOUBLE NOT NULL,
            required_sample_per_arm BIGINT NOT NULL,
            observed_min_sample_per_arm BIGINT NOT NULL,
            sample_size_met BOOLEAN NOT NULL,
            guardrail_passed BOOLEAN NOT NULL,
            is_statistically_significant BOOLEAN NOT NULL,
            decision VARCHAR NOT NULL,
            seed INTEGER NOT NULL,
            data_origin VARCHAR NOT NULL
        )
        """
    )
    for scenario_id, spec in SCENARIO_SPECS.items():
        rows = connection.execute(
            """
            SELECT experiment_group, assigned_users, converted_users, refund_rate
            FROM synthetic.experiment_arm_metrics
            WHERE scenario_id = ?
            ORDER BY experiment_group
            """,
            [scenario_id],
        ).fetchall()
        arms = {
            group: {
                "assigned": int(assigned),
                "converted": int(converted),
                "refund_rate": float(refund_rate),
            }
            for group, assigned, converted, refund_rate in rows
        }
        control = arms["control"]
        variant = arms["variant"]
        control_rate = control["converted"] / control["assigned"]
        variant_rate = variant["converted"] / variant["assigned"]
        difference = variant_rate - control_rate
        relative_lift = difference / control_rate
        pooled = (control["converted"] + variant["converted"]) / (
            control["assigned"] + variant["assigned"]
        )
        null_standard_error = math.sqrt(
            pooled
            * (1 - pooled)
            * (1 / control["assigned"] + 1 / variant["assigned"])
        )
        z_statistic = difference / null_standard_error
        p_value = math.erfc(abs(z_statistic) / math.sqrt(2))
        interval_standard_error = math.sqrt(
            control_rate * (1 - control_rate) / control["assigned"]
            + variant_rate * (1 - variant_rate) / variant["assigned"]
        )
        confidence_low = difference - CONFIDENCE_Z * interval_standard_error
        confidence_high = difference + CONFIDENCE_Z * interval_standard_error
        observed_min_sample = min(control["assigned"], variant["assigned"])
        sample_size_met = observed_min_sample >= REQUIRED_SAMPLE_PER_ARM
        guardrail_passed = (
            variant["refund_rate"] - control["refund_rate"] <= 0.01
        )
        significant = p_value < ALPHA
        if significant and confidence_low > 0 and sample_size_met and guardrail_passed:
            decision = "candidate_for_gradual_rollout"
        else:
            decision = "do_not_roll_out_based_on_current_evidence"

        connection.execute(
            """
            INSERT INTO synthetic.experiment_results VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                scenario_id,
                spec["name_cn"],
                "assignment_cvr",
                control_rate,
                variant_rate,
                difference,
                relative_lift,
                confidence_low,
                confidence_high,
                z_statistic,
                p_value,
                ALPHA,
                REQUIRED_SAMPLE_PER_ARM,
                observed_min_sample,
                sample_size_met,
                guardrail_passed,
                significant,
                decision,
                seed,
                DATA_ORIGIN,
            ],
        )


def _run_quality_checks(connection: Any, seed: int) -> list[dict[str, Any]]:
    expected_rows = len(SCENARIO_SPECS) * 2 * PARTICIPANTS_PER_ARM
    definitions = [
        (
            "synthetic_assignment_row_count",
            "blocking",
            "SELECT count(*) FROM synthetic.experiment_assignment",
            expected_rows,
            "模拟分配行数等于两场景、两组的预设样本量",
        ),
        (
            "synthetic_origin_only",
            "blocking",
            "SELECT count(*) FROM synthetic.experiment_assignment "
            "WHERE data_origin <> 'synthetic'",
            0,
            "所有模拟明细均标记 synthetic",
        ),
        (
            "synthetic_identifier_prefix",
            "blocking",
            "SELECT count(*) FROM synthetic.experiment_assignment "
            f"WHERE participant_id NOT LIKE 'sim_{seed}_%'",
            0,
            "模拟参与者使用独立 sim_ 前缀且包含固定种子",
        ),
        (
            "conversion_requires_click",
            "blocking",
            "SELECT count(*) FROM synthetic.experiment_assignment "
            "WHERE was_converted AND NOT was_clicked",
            0,
            "模拟转化均发生在点击之后",
        ),
        (
            "converted_order_contract",
            "blocking",
            "SELECT count(*) FROM synthetic.experiment_assignment WHERE "
            "(was_converted AND (order_id IS NULL OR order_amount IS NULL)) OR "
            "(NOT was_converted AND (order_id IS NOT NULL OR order_amount IS NOT NULL))",
            0,
            "转化标记、模拟订单和模拟金额保持一致",
        ),
        (
            "sample_size_per_arm",
            "blocking",
            "SELECT count(*) FROM synthetic.experiment_arm_metrics "
            f"WHERE assigned_users <> {PARTICIPANTS_PER_ARM}",
            0,
            "每个实验组达到预登记最小样本量",
        ),
        (
            "scenario_effect_contract",
            "blocking",
            "SELECT count(*) FROM synthetic.experiment_results WHERE "
            "(scenario_id = 'no_effect' AND abs(absolute_lift) > 0.000000001) OR "
            "(scenario_id = 'positive_effect' AND abs(absolute_lift - 0.012) > 0.000000001)",
            0,
            "无效果和正向效果场景符合预登记生成口径",
        ),
        (
            "aggregate_export_origin",
            "blocking",
            "SELECT count(*) FROM synthetic.experiment_results "
            "WHERE data_origin <> 'synthetic'",
            0,
            "实验统计结果保持模拟来源标记",
        ),
    ]
    if connection.execute(
        """
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'core' AND table_name = 'fct_event'
        """
    ).fetchone()[0]:
        definitions.append(
            (
                "no_real_visitorid_reuse",
                "blocking",
                "SELECT count(*) FROM synthetic.experiment_assignment AS simulated "
                "INNER JOIN core.fct_event AS real "
                "ON simulated.participant_id = cast(real.visitorid AS VARCHAR)",
                0,
                "模拟参与者 ID 不复用真实 visitorid",
            )
        )

    checks: list[dict[str, Any]] = []
    for check_id, severity, query, expected, description in definitions:
        actual = connection.execute(query).fetchone()[0]
        passed = actual == expected
        checks.append(
            {
                "check_id": check_id,
                "severity": severity,
                "status": "pass" if passed else "fail",
                "actual_value": actual,
                "expected_value": expected,
                "description_cn": description,
            }
        )
    return checks


def _export_experiment_aggregates(
    connection: Any,
    export_directory: Path,
    run_id: str,
    seed: int,
) -> dict[str, Any]:
    export_root = export_directory / "v0.5.0-simulated"
    temporary_root = export_root / f".tmp-{run_id}"
    export_root.mkdir(parents=True, exist_ok=True)
    temporary_root.mkdir(parents=True, exist_ok=False)
    exported: list[dict[str, Any]] = []
    try:
        for relation in EXPORT_RELATIONS:
            file_stem = relation.replace(".", "__")
            for suffix, options in (
                ("csv", "FORMAT CSV, HEADER TRUE"),
                ("parquet", "FORMAT PARQUET, COMPRESSION ZSTD"),
            ):
                temporary_path = temporary_root / f"{file_stem}.{suffix}"
                connection.execute(
                    f"COPY (SELECT * FROM {relation} ORDER BY ALL) "
                    f"TO {sql_literal(temporary_path)} ({options})"
                )
                final_path = export_root / temporary_path.name
                temporary_path.replace(final_path)
                exported.append(
                    {
                        "relation": relation,
                        "format": suffix,
                        "path": final_path.name,
                        "rows": connection.execute(
                            f"SELECT count(*) FROM {relation}"
                        ).fetchone()[0],
                        "bytes": final_path.stat().st_size,
                        "sha256": _hash_file(final_path),
                    }
                )
        manifest = {
            "milestone": MILESTONE,
            "data_origin": DATA_ORIGIN,
            "snapshot_kind": "synthetic_aggregate_export",
            "seed": seed,
            "contains_visitor_level_exports": False,
            "contains_real_retailrocket_data": False,
            "files": exported,
            "limitations": [
                "All channel, amount, and experiment fields are simulated.",
                "The results demonstrate analysis methods and are not observed business impact.",
                "Only aggregate relations are exported; participant assignments remain local.",
            ],
        }
        manifest_path = export_root / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)
    return {
        "export_directory": str(export_root),
        "manifest_path": str(manifest_path),
        "files": exported,
    }


def _simulation_input_hash(seed: int) -> str:
    payload = {
        "seed": seed,
        "participants_per_arm": PARTICIPANTS_PER_ARM,
        "required_sample_per_arm": REQUIRED_SAMPLE_PER_ARM,
        "scenarios": SCENARIO_SPECS,
        "channels": CHANNELS,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _fetch_dicts(connection: Any, query: str) -> list[dict[str, Any]]:
    rows = connection.execute(query).fetchall()
    columns = [item[0] for item in connection.description]
    return [dict(zip(columns, row, strict=True)) for row in rows]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
