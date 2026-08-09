# SQL model placeholders

This directory reserves the dependency order for the DuckDB warehouse:

1. `meta` — run metadata, source manifests, and lineage.
2. `raw` — lossless copies of the official full Retailrocket CSV files.
3. `stg` — typed, normalized, and quality-flagged source records.
4. `core` — event, session, transaction, item-history, and category entities.
5. `mart` — versioned operations metrics consumed by Python and Streamlit.

The SQL files in `v0.1.0` are harmless marker queries. They are not an ingest or
warehouse implementation and must not be glob-executed as a pipeline. The real
models, their contracts, and their tests belong to Goal 2 and Goal 3.

The official full dataset at
`D:\CodexData\product-ops-growth-analytics\raw\extracted` is the sole formal
analysis source. Sample files are excluded from the model graph.
