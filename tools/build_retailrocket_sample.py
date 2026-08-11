from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
SESSION_GAP_MS = 30 * 60 * 1000
EVENT_COLUMNS = ["timestamp", "visitorid", "event", "itemid", "transactionid"]


def read_events(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype={
            "timestamp": "int64",
            "visitorid": "int64",
            "event": "category",
            "itemid": "int64",
            "transactionid": "Int64",
        },
    )


def add_session_fields(events: pd.DataFrame) -> pd.DataFrame:
    result = events.sort_values(["visitorid", "timestamp", "itemid"], kind="mergesort").copy()
    gaps = result.groupby("visitorid", sort=False)["timestamp"].diff()
    new_session = gaps.isna() | gaps.gt(SESSION_GAP_MS)
    result["session_number"] = new_session.groupby(result["visitorid"]).cumsum().astype("int64")
    result["event_sequence"] = result.groupby("visitorid", sort=False).cumcount() + 1
    return result


def choose_journey_visitors(events_with_sessions: pd.DataFrame) -> tuple[list[int], pd.DataFrame]:
    session_summary = (
        events_with_sessions.groupby(["visitorid", "session_number", "event"], observed=True)["timestamp"]
        .min()
        .unstack("event")
    )
    for column in ["view", "addtocart", "transaction"]:
        if column not in session_summary.columns:
            session_summary[column] = np.nan

    complete = session_summary.dropna(subset=["view", "addtocart", "transaction"])
    complete = complete[
        (complete["view"] < complete["addtocart"])
        & (complete["addtocart"] < complete["transaction"])
    ]
    candidates = complete.reset_index()["visitorid"].drop_duplicates()

    visitor_sizes = events_with_sessions.groupby("visitorid", sort=False).size()
    manageable = candidates[candidates.map(visitor_sizes).between(3, 200)]
    pool = manageable if len(manageable) >= 20 else candidates
    if len(pool) < 20:
        raise RuntimeError(f"仅找到 {len(pool)} 个完整有序路径访客，少于要求的 20 个")

    selected = (
        pool.sample(n=20, random_state=SEED)
        .astype("int64")
        .sort_values()
        .tolist()
    )
    journeys = events_with_sessions[events_with_sessions["visitorid"].isin(selected)].copy()
    journeys = journeys.sort_values(["visitorid", "timestamp", "itemid"], kind="mergesort")
    return selected, journeys


def read_matching_properties(paths: list[Path], item_ids: set[int], limit: int = 5000) -> pd.DataFrame:
    matches: list[pd.DataFrame] = []
    for path in paths:
        for chunk in pd.read_csv(
            path,
            chunksize=500_000,
            dtype={"timestamp": "int64", "itemid": "int64", "property": "string", "value": "string"},
        ):
            subset = chunk[chunk["itemid"].isin(item_ids)]
            if not subset.empty:
                matches.append(subset)

    if not matches:
        return pd.DataFrame(columns=["timestamp", "itemid", "property", "value"])

    properties = pd.concat(matches, ignore_index=True)
    meaningful = properties[properties["property"].isin(["categoryid", "available"])]
    anonymous = properties[~properties["property"].isin(["categoryid", "available"])]
    remaining = max(0, limit - len(meaningful))
    if len(anonymous) > remaining:
        anonymous = anonymous.sample(n=remaining, random_state=SEED)
    properties = pd.concat([meaningful, anonymous], ignore_index=True)
    properties["_priority"] = properties["property"].map({"categoryid": 0, "available": 1}).fillna(2)
    return (
        properties.sort_values(["_priority", "itemid", "property", "timestamp"], kind="mergesort")
        .drop(columns="_priority")
        .reset_index(drop=True)
    )


def relevant_category_tree(tree_path: Path, properties: pd.DataFrame) -> pd.DataFrame:
    tree = pd.read_csv(tree_path, dtype={"categoryid": "int64", "parentid": "Int64"})
    category_values = properties.loc[properties["property"].eq("categoryid"), "value"]
    direct_ids = set(pd.to_numeric(category_values, errors="coerce").dropna().astype("int64"))
    relevant = set(direct_ids)
    parent_map = tree.set_index("categoryid")["parentid"].to_dict()
    frontier = list(direct_ids)
    while frontier:
        current = frontier.pop()
        parent = parent_map.get(current)
        if parent is not None and not pd.isna(parent):
            parent_int = int(parent)
            if parent_int not in relevant:
                relevant.add(parent_int)
                frontier.append(parent_int)
    return tree[tree["categoryid"].isin(relevant)].sort_values("categoryid").reset_index(drop=True)


def json_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def records_for_workbook(frame: pd.DataFrame) -> list[list]:
    return [[json_value(value) for value in row] for row in frame.itertuples(index=False, name=None)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = args.output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    events = read_events(args.input_dir / "events.csv")
    random_sample = events.sample(n=2000, random_state=SEED).sort_index()[EVENT_COLUMNS].copy()
    events_with_sessions = add_session_fields(events)
    selected_visitors, journeys_full = choose_journey_visitors(events_with_sessions)
    journeys_raw = journeys_full[EVENT_COLUMNS].copy()

    item_ids = set(journeys_raw["itemid"].astype("int64"))
    properties = read_matching_properties(
        [args.input_dir / "item_properties_part1.csv", args.input_dir / "item_properties_part2.csv"],
        item_ids,
    )
    categories = relevant_category_tree(args.input_dir / "category_tree.csv", properties)
    property_item_ids = set(properties["itemid"].astype("int64"))
    category_values = set(
        pd.to_numeric(
            properties.loc[properties["property"].eq("categoryid"), "value"], errors="coerce"
        ).dropna().astype("int64")
    )
    category_tree_ids = set(categories["categoryid"].astype("int64"))

    random_path = csv_dir / "events_random_2000.csv"
    journeys_path = csv_dir / "events_journeys.csv"
    props_path = csv_dir / "item_properties_sample.csv"
    categories_path = csv_dir / "category_tree_sample.csv"
    random_sample.to_csv(random_path, index=False)
    journeys_raw.to_csv(journeys_path, index=False)
    properties.to_csv(props_path, index=False)
    categories.to_csv(categories_path, index=False)

    # Preserve session and sequence values calculated from the complete event history,
    # rather than recomputing them inside the sparse 2,000-row sample.
    random_excel = events_with_sessions.loc[random_sample.index].copy()
    random_excel["event_time"] = pd.to_datetime(random_excel["timestamp"], unit="ms", utc=True).dt.tz_localize(None)
    random_excel["event_cn"] = random_excel["event"].map(
        {"view": "浏览", "addtocart": "加入购物车", "transaction": "交易"}
    ).astype("string")
    random_excel["has_transaction_id"] = random_excel["transactionid"].notna()
    random_excel = random_excel[
        EVENT_COLUMNS + ["event_time", "event_cn", "has_transaction_id", "event_sequence", "session_number"]
    ]

    journeys_excel = journeys_full.copy()
    journeys_excel["event_time"] = pd.to_datetime(journeys_excel["timestamp"], unit="ms", utc=True).dt.tz_localize(None)
    journeys_excel["event_cn"] = journeys_excel["event"].map(
        {"view": "浏览", "addtocart": "加入购物车", "transaction": "交易"}
    ).astype("string")
    journeys_excel["has_transaction_id"] = journeys_excel["transactionid"].notna()
    journeys_excel = journeys_excel[
        EVENT_COLUMNS + ["event_time", "event_cn", "has_transaction_id", "event_sequence", "session_number"]
    ]

    props_excel = properties.copy()
    props_excel["property_time"] = pd.to_datetime(props_excel["timestamp"], unit="ms", utc=True).dt.tz_localize(None)
    props_excel["property_meaning_cn"] = props_excel["property"].map(
        {"categoryid": "商品分类ID", "available": "是否可售：1可售，0不可售"}
    ).fillna("匿名属性，不作业务解释")
    props_excel = props_excel[["timestamp", "itemid", "property", "value", "property_time", "property_meaning_cn"]]

    workbook_data = {
        "metadata": {
            "source_url": "https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset",
            "license_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            "license": "CC BY-NC-SA 4.0",
            "seed": SEED,
            "session_gap_minutes": 30,
            "journey_item_property_coverage": len(item_ids & property_item_ids) / len(item_ids),
            "category_tree_coverage": (
                len(category_values & category_tree_ids) / len(category_values) if category_values else None
            ),
            "selected_visitors": selected_visitors,
            "counts": {
                "random_events": len(random_sample),
                "journey_events": len(journeys_raw),
                "journey_visitors": journeys_raw["visitorid"].nunique(),
                "property_rows": len(properties),
                "category_rows": len(categories),
            },
            "event_counts_random": {
                str(key): int(value) for key, value in random_sample["event"].value_counts().items()
            },
            "event_counts_journeys": {
                str(key): int(value) for key, value in journeys_raw["event"].value_counts().items()
            },
        },
        "sheets": {
            "随机事件样例": {
                "headers": list(random_excel.columns),
                "rows": records_for_workbook(random_excel),
            },
            "完整行为路径": {
                "headers": list(journeys_excel.columns),
                "rows": records_for_workbook(journeys_excel),
            },
            "商品属性": {
                "headers": list(props_excel.columns),
                "rows": records_for_workbook(props_excel),
            },
            "分类树": {
                "headers": list(categories.columns),
                "rows": records_for_workbook(categories),
            },
        },
    }
    with (args.output_dir / "workbook_data.json").open("w", encoding="utf-8") as handle:
        json.dump(workbook_data, handle, ensure_ascii=False, default=str)

    print(json.dumps(workbook_data["metadata"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
