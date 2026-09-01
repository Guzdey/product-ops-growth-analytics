# DuckDB SQL models

Goal 2 executes this directory in the following dependency order:

1. `meta` — run metadata, source manifests, and lineage.
2. `raw` — lossless copies of the official full Retailrocket CSV files.
3. `stg` — typed, normalized, and quality-flagged source records.
4. `core` — event, session, transaction, item-history, and category entities.
5. `mart` — versioned operations metrics consumed by Python and Streamlit (Goal 3).

Python loads an explicit list of SQL files; it does not execute arbitrary files
found by glob. SQL owns table definitions and transformations, while Python owns
file inspection, ordered execution, run metadata, validation, and reporting.

The official full dataset at
`D:\CodexData\product-ops-growth-analytics\raw\extracted` is the sole formal
analysis source. Sample files are excluded from the model graph.
