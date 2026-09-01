# `raw` layer

`001_ingest.sql` reads the four official CSV files with explicit DuckDB types.
It preserves every source row and adds only lineage columns. The two item
property files are combined without dropping anonymous attributes.
