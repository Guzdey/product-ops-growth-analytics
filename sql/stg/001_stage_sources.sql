CREATE OR REPLACE TABLE stg.events AS
WITH profiled AS (
    SELECT
        raw.*,
        count(*) OVER (
            PARTITION BY "timestamp", visitorid, event, itemid, transactionid
        ) AS exact_duplicate_count
    FROM raw.events AS raw
)

SELECT
    md5(source_id || ':' || source_row_number::VARCHAR) AS event_id,
    source_row_number,
    "timestamp" AS event_timestamp_ms,
    CASE WHEN "timestamp" IS NULL THEN NULL ELSE make_timestamp_ms("timestamp") END
        AS event_time_utc,
    visitorid,
    event,
    itemid,
    transactionid,
    source_id,
    source_file,
    exact_duplicate_count > 1 AS is_exact_duplicate,
    event NOT IN ('view', 'addtocart', 'transaction') OR event IS NULL
        AS is_unknown_event,
    "timestamp" IS NULL OR visitorid IS NULL OR event IS NULL OR itemid IS NULL
        AS has_required_null,
    (event = 'transaction' AND transactionid IS NULL)
    OR (event <> 'transaction' AND transactionid IS NOT NULL)
        AS has_transaction_id_mismatch
FROM profiled;

CREATE OR REPLACE TABLE stg.item_property_value_stats AS
SELECT
    "timestamp",
    itemid,
    property,
    value,
    count(*) AS source_row_count
FROM raw.item_properties
GROUP BY "timestamp", itemid, property, value;

CREATE OR REPLACE TABLE stg.item_property_timestamp_stats AS
SELECT
    "timestamp",
    itemid,
    property,
    count(*) AS distinct_value_count
FROM stg.item_property_value_stats
GROUP BY "timestamp", itemid, property;

CREATE OR REPLACE TABLE stg.item_properties AS
WITH profiled AS (
    SELECT
        raw.*,
        value_stats.source_row_count AS exact_duplicate_count,
        timestamp_stats.distinct_value_count AS timestamp_value_count
    FROM raw.item_properties AS raw
    INNER JOIN stg.item_property_value_stats AS value_stats
        ON
            raw."timestamp" IS NOT DISTINCT FROM value_stats."timestamp"
            AND raw.itemid IS NOT DISTINCT FROM value_stats.itemid
            AND raw.property IS NOT DISTINCT FROM value_stats.property
            AND raw.value IS NOT DISTINCT FROM value_stats.value
    INNER JOIN stg.item_property_timestamp_stats AS timestamp_stats
        ON
            raw."timestamp" IS NOT DISTINCT FROM timestamp_stats."timestamp"
            AND raw.itemid IS NOT DISTINCT FROM timestamp_stats.itemid
            AND raw.property IS NOT DISTINCT FROM timestamp_stats.property
)

SELECT
    source_row_number,
    "timestamp" AS property_timestamp_ms,
    CASE WHEN "timestamp" IS NULL THEN NULL ELSE make_timestamp_ms("timestamp") END
        AS property_time_utc,
    itemid,
    property,
    value,
    CASE WHEN property = 'categoryid' THEN try_cast(value AS BIGINT) END
        AS categoryid_value,
    CASE WHEN property = 'available' THEN try_cast(value AS INTEGER) END
        AS available_value,
    source_id,
    source_file,
    exact_duplicate_count > 1 AS is_exact_duplicate,
    timestamp_value_count > 1 AS has_timestamp_conflict,
    "timestamp" IS NULL OR itemid IS NULL OR property IS NULL AS has_required_null,
    property = 'categoryid' AND value IS NOT NULL
    AND try_cast(value AS BIGINT) IS NULL AS has_invalid_categoryid,
    property = 'available' AND value IS NOT NULL
    AND try_cast(value AS INTEGER) IS NULL AS has_invalid_available
FROM profiled;

CREATE OR REPLACE TABLE stg.category_tree AS
WITH profiled AS (
    SELECT
        raw.*,
        count(*) OVER (PARTITION BY categoryid) AS category_record_count
    FROM raw.category_tree AS raw
)

SELECT
    source_row_number,
    categoryid,
    parentid,
    source_id,
    source_file,
    category_record_count > 1 AS is_duplicate_category,
    categoryid = parentid AS is_self_reference,
    categoryid IS NULL AS has_required_null
FROM profiled;
