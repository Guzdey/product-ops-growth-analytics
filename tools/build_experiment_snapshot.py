"""Build the small public simulated-experiment snapshot from aggregate exports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from product_ops.dashboard import (
    DEFAULT_EXPERIMENT_EXPORT_DIRECTORY,
    EXPERIMENT_TABLE_FILES,
    bundled_experiment_directory,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_EXPERIMENT_EXPORT_DIRECTORY,
        help="Validated v0.5.0 synthetic aggregate export directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=bundled_experiment_directory(),
        help="Repository aggregate snapshot directory",
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
    if source_manifest.get("data_origin") != "synthetic":
        raise ValueError("Source export must have data_origin='synthetic'")
    if source_manifest.get("contains_real_retailrocket_data") is not False:
        raise ValueError("Source export must explicitly exclude real Retailrocket data")

    output.mkdir(parents=True, exist_ok=True)
    generated_files: list[dict[str, object]] = []
    for table_name, filename in EXPERIMENT_TABLE_FILES.items():
        source_path = source / filename
        output_path = output / filename
        normalized = source_path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        output_path.write_bytes(normalized)
        frame = pd.read_csv(output_path)
        forbidden = {"visitorid", "transactionid", "session_id", "participant_id", "order_id"}
        exposed = forbidden.intersection(frame.columns)
        if exposed:
            raise ValueError(f"Public experiment snapshot exposes identifiers: {sorted(exposed)}")
        if set(frame["data_origin"].astype(str)) != {"synthetic"}:
            raise ValueError(f"Unexpected data origin in {filename}")
        generated_files.append(
            {
                "table": table_name,
                "path": filename,
                "rows": len(frame),
                "bytes": output_path.stat().st_size,
                "sha256": file_sha256(output_path),
                "selection": "all aggregate rows",
            }
        )

    manifest: dict[str, object] = {
        "milestone": "v0.5.0",
        "data_origin": "synthetic",
        "snapshot_kind": "public_simulated_aggregate_snapshot",
        "seed": source_manifest["seed"],
        "contains_visitor_level_exports": False,
        "contains_real_retailrocket_data": False,
        "files": generated_files,
        "limitations": source_manifest["limitations"],
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
        f"Built {len(manifest['files'])} simulated dashboard tables "
        f"({total_bytes / 1024:.1f} KiB) in {args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
