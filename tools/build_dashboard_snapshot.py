"""Build the small public dashboard snapshot from validated v0.3 aggregate exports."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from product_ops.dashboard import DEFAULT_FULL_EXPORT_DIRECTORY, TABLE_FILES

FULL_COPY_TABLES = frozenset(TABLE_FILES) - {"session_path_summary", "item_performance"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_FULL_EXPORT_DIRECTORY,
        help="Validated v0.3.0 aggregate export directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "demo_data" / "v0.4.0",
        help="Small public snapshot directory",
    )
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_snapshot(source: Path, output: Path) -> dict[str, object]:
    source_manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if source_manifest.get("data_origin") != "real":
        raise ValueError("Source export must have data_origin='real'")

    output.mkdir(parents=True, exist_ok=True)
    generated_files: list[dict[str, object]] = []

    for table_name, filename in TABLE_FILES.items():
        source_path = source / filename
        output_path = output / filename
        if table_name in FULL_COPY_TABLES:
            source_bytes = source_path.read_bytes()
            normalized_bytes = source_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            output_path.write_bytes(normalized_bytes)
            frame = pd.read_csv(output_path)
            selection = "all aggregate rows"
        else:
            frame = pd.read_csv(source_path)
            if table_name == "session_path_summary":
                frame = frame.nlargest(50, "session_count").sort_values(
                    "session_count", ascending=False
                )
                selection = "top 50 paths by session_count"
            else:
                top_overall = frame.nlargest(250, "view_session_count")
                focus_category = frame.loc[frame["categoryid"] == 299].nlargest(
                    50, "view_session_count"
                )
                frame = (
                    pd.concat([top_overall, focus_category])
                    .drop_duplicates(subset=["itemid"])
                    .sort_values("view_session_count", ascending=False)
                )
                selection = "top 250 items plus up to 50 items in focus category 299"
            frame.to_csv(output_path, index=False, lineterminator="\n")

        forbidden = {"visitorid", "transactionid", "session_id"}.intersection(frame.columns)
        if forbidden:
            raise ValueError(f"Public snapshot exposes forbidden columns: {sorted(forbidden)}")
        if set(frame["data_origin"].astype(str)) != {"real"}:
            raise ValueError(f"Unexpected data origin in {filename}")
        generated_files.append(
            {
                "table": table_name,
                "path": filename,
                "rows": len(frame),
                "bytes": output_path.stat().st_size,
                "sha256": file_sha256(output_path),
                "selection": selection,
            }
        )

    manifest: dict[str, object] = {
        "milestone": "v0.4.0",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "data_origin": "real",
        "snapshot_kind": "public_aggregate_snapshot",
        "source_milestone": source_manifest.get("milestone"),
        "source_run_id": source_manifest.get("run_id"),
        "contains_visitor_level_exports": False,
        "contains_transaction_level_exports": False,
        "limitations": [
            "High-cardinality session paths and item rows are limited for public display.",
            "All dashboard metrics remain aggregates calculated by the v0.3 SQL marts.",
            "The snapshot is not a replacement for the official full Retailrocket CSV files.",
        ],
        "files": generated_files,
    }
    (output / "dashboard_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> int:
    args = parse_args()
    manifest = build_snapshot(args.source.resolve(), args.output.resolve())
    total_bytes = sum(int(item["bytes"]) for item in manifest["files"])
    print(
        f"Built {len(manifest['files'])} dashboard tables "
        f"({total_bytes / 1024:.1f} KiB) in {args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
