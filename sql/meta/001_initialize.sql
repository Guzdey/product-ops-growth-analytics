CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS meta.pipeline_run (
    run_id VARCHAR PRIMARY KEY,
    command VARCHAR NOT NULL,
    started_at_utc TIMESTAMPTZ NOT NULL,
    finished_at_utc TIMESTAMPTZ,
    status VARCHAR NOT NULL,
    input_hash VARCHAR,
    code_version VARCHAR NOT NULL,
    error_summary VARCHAR
);

CREATE TABLE IF NOT EXISTS meta.source_file_manifest (
    source_id VARCHAR PRIMARY KEY,
    absolute_path VARCHAR NOT NULL,
    file_name VARCHAR NOT NULL,
    byte_size BIGINT NOT NULL,
    sha256 VARCHAR NOT NULL,
    modified_at_utc TIMESTAMPTZ NOT NULL,
    expected_row_count BIGINT,
    actual_row_count BIGINT NOT NULL,
    ingest_run_id VARCHAR NOT NULL,
    imported_at_utc TIMESTAMPTZ NOT NULL,
    code_version VARCHAR NOT NULL,
    data_origin VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS meta.quality_check (
    run_id VARCHAR NOT NULL,
    check_id VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    actual_value VARCHAR NOT NULL,
    expected_value VARCHAR NOT NULL,
    description_cn VARCHAR NOT NULL,
    checked_at_utc TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (run_id, check_id)
);

CREATE TABLE IF NOT EXISTS meta.model_build_step (
    step_run_id VARCHAR PRIMARY KEY,
    pipeline_run_id VARCHAR NOT NULL,
    step_name VARCHAR NOT NULL,
    step_order INTEGER NOT NULL,
    target_relation VARCHAR,
    statement_sha256 VARCHAR NOT NULL,
    build_signature VARCHAR NOT NULL,
    started_at_utc TIMESTAMPTZ NOT NULL,
    finished_at_utc TIMESTAMPTZ,
    status VARCHAR NOT NULL,
    row_count BIGINT,
    error_summary VARCHAR
);
