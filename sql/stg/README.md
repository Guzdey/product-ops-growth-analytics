# `stg` layer

`001_stage_sources.sql` converts epoch milliseconds to UTC timestamps and adds
non-destructive flags for exact duplicates, unknown events, missing required
values, transaction-ID mismatches, invalid typed properties, and timestamp
conflicts. Source rows remain present even when a flag is true.
