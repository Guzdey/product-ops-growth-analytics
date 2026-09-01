# `meta` layer

`001_initialize.sql` creates the five schemas plus three audit tables:

- `meta.source_file_manifest` records source paths, sizes, SHA-256 hashes, row
  counts, import time, code revision, and data origin.
- `meta.pipeline_run` records each CLI step and its final status.
- `meta.quality_check` stores machine-readable validation results.
