CREATE OR REPLACE TABLE core.fct_event AS
WITH ordered AS (
    SELECT
        stg.*,
        lag(event_timestamp_ms) OVER (
            PARTITION BY visitorid
            ORDER BY event_timestamp_ms, event_id
        ) AS previous_event_timestamp_ms
    FROM stg.events AS stg
),

boundaries AS (
    SELECT
        *,
        CASE
            WHEN previous_event_timestamp_ms IS NULL THEN 1
            WHEN
                event_timestamp_ms - previous_event_timestamp_ms
                > {{ session_gap_milliseconds }} THEN 1
            ELSE 0
        END AS starts_new_session
    FROM ordered
),

numbered AS (
    SELECT
        *,
        sum(starts_new_session) OVER (
            PARTITION BY visitorid
            ORDER BY event_timestamp_ms, event_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )::BIGINT AS visitor_session_number
    FROM boundaries
)

SELECT
    event_id,
    visitorid,
    event_timestamp_ms,
    event_time_utc,
    event,
    itemid,
    transactionid,
    visitor_session_number,
    md5(visitorid::VARCHAR || ':' || visitor_session_number::VARCHAR) AS session_id,
    row_number() OVER (
        PARTITION BY visitorid, visitor_session_number
        ORDER BY event_timestamp_ms, event_id
    )::BIGINT AS event_number_in_session,
    source_row_number,
    source_id,
    source_file,
    is_exact_duplicate,
    is_unknown_event,
    has_required_null,
    has_transaction_id_mismatch
FROM numbered;

CREATE OR REPLACE TABLE core.fct_session AS
SELECT
    session_id,
    visitorid,
    visitor_session_number,
    min(event_time_utc) AS session_start_utc,
    max(event_time_utc) AS session_end_utc,
    date_diff('second', min(event_time_utc), max(event_time_utc))
        AS session_duration_seconds,
    count(*) AS event_count,
    count(DISTINCT itemid) AS distinct_item_count,
    count(*) FILTER (WHERE event = 'view') AS view_event_count,
    count(*) FILTER (WHERE event = 'addtocart') AS addtocart_event_count,
    count(*) FILTER (WHERE event = 'transaction') AS transaction_event_count,
    count(DISTINCT transactionid) FILTER (WHERE event = 'transaction')
        AS distinct_transaction_count,
    bool_or(has_required_null OR is_unknown_event OR has_transaction_id_mismatch)
        AS has_event_quality_issue
FROM core.fct_event
GROUP BY session_id, visitorid, visitor_session_number;

CREATE OR REPLACE TABLE core.fct_transaction AS
SELECT
    transactionid,
    min(visitorid) AS visitorid,
    min(event_time_utc) AS transaction_time_utc,
    max(event_time_utc) AS last_transaction_event_time_utc,
    count(*) AS transaction_event_count,
    count(DISTINCT itemid) AS distinct_item_count,
    count(DISTINCT visitorid) AS visitor_count,
    count(DISTINCT session_id) AS session_count,
    count(DISTINCT visitorid) > 1 AS has_multiple_visitors,
    count(DISTINCT session_id) > 1 AS spans_multiple_sessions
FROM core.fct_event
WHERE event = 'transaction' AND transactionid IS NOT NULL
GROUP BY transactionid;

CREATE OR REPLACE TABLE core.item_property_history AS
WITH timestamp_bounds AS (
    SELECT
        itemid,
        property,
        "timestamp" AS property_timestamp_ms,
        make_timestamp_ms("timestamp") AS valid_from_utc,
        lead(make_timestamp_ms("timestamp")) OVER (
            PARTITION BY itemid, property
            ORDER BY "timestamp"
        ) AS valid_to_utc
    FROM stg.item_property_timestamp_stats
    WHERE "timestamp" IS NOT NULL AND itemid IS NOT NULL AND property IS NOT NULL
),

values_at_timestamp AS (
    SELECT
        value_stats.itemid,
        value_stats.property,
        value_stats."timestamp" AS property_timestamp_ms,
        value_stats.value,
        value_stats.source_row_count,
        value_stats.source_row_count > 1 AS has_exact_duplicate,
        timestamp_stats.distinct_value_count > 1 AS has_timestamp_conflict
    FROM stg.item_property_value_stats AS value_stats
    INNER JOIN stg.item_property_timestamp_stats AS timestamp_stats
        ON
            value_stats."timestamp" IS NOT DISTINCT FROM timestamp_stats."timestamp"
            AND value_stats.itemid IS NOT DISTINCT FROM timestamp_stats.itemid
            AND value_stats.property IS NOT DISTINCT FROM timestamp_stats.property
    WHERE
        value_stats."timestamp" IS NOT NULL
        AND value_stats.itemid IS NOT NULL
        AND value_stats.property IS NOT NULL
)

SELECT
    values_at_timestamp.itemid,
    values_at_timestamp.property,
    values_at_timestamp.value,
    timestamp_bounds.valid_from_utc,
    timestamp_bounds.valid_to_utc,
    values_at_timestamp.source_row_count,
    values_at_timestamp.has_exact_duplicate,
    values_at_timestamp.has_timestamp_conflict
FROM values_at_timestamp
INNER JOIN timestamp_bounds USING (itemid, property, property_timestamp_ms);

CREATE OR REPLACE TABLE core.item_category_history AS
WITH snapshots AS (
    SELECT
        itemid,
        property_timestamp_ms,
        property_time_utc AS valid_from_utc,
        count(DISTINCT value) AS distinct_value_count,
        count(*) FILTER (WHERE categoryid_value IS NULL) AS invalid_value_count,
        min(categoryid_value) AS parsed_categoryid,
        count(*) AS source_row_count
    FROM stg.item_properties
    WHERE property = 'categoryid' AND NOT has_required_null
    GROUP BY itemid, property_timestamp_ms, property_time_utc
)

SELECT
    itemid,
    CASE
        WHEN distinct_value_count = 1 AND invalid_value_count = 0
            THEN parsed_categoryid
    END AS categoryid,
    valid_from_utc,
    lead(valid_from_utc) OVER (
        PARTITION BY itemid ORDER BY property_timestamp_ms
    ) AS valid_to_utc,
    source_row_count,
    distinct_value_count > 1 AS has_timestamp_conflict,
    invalid_value_count > 0 AS has_invalid_value,
    distinct_value_count = 1 AND invalid_value_count = 0 AS is_valid_snapshot
FROM snapshots;

CREATE OR REPLACE TABLE core.item_availability_history AS
WITH snapshots AS (
    SELECT
        itemid,
        property_timestamp_ms,
        property_time_utc AS valid_from_utc,
        count(DISTINCT value) AS distinct_value_count,
        count(*) FILTER (WHERE available_value IS NULL) AS invalid_value_count,
        min(available_value) AS parsed_available,
        count(*) AS source_row_count
    FROM stg.item_properties
    WHERE property = 'available' AND NOT has_required_null
    GROUP BY itemid, property_timestamp_ms, property_time_utc
)

SELECT
    itemid,
    CASE
        WHEN distinct_value_count = 1 AND invalid_value_count = 0
            THEN parsed_available
    END AS available,
    valid_from_utc,
    lead(valid_from_utc) OVER (
        PARTITION BY itemid ORDER BY property_timestamp_ms
    ) AS valid_to_utc,
    source_row_count,
    distinct_value_count > 1 AS has_timestamp_conflict,
    invalid_value_count > 0 AS has_invalid_value,
    distinct_value_count = 1 AND invalid_value_count = 0 AS is_valid_snapshot
FROM snapshots;

CREATE OR REPLACE TABLE core.fct_event_item_context AS
WITH event_with_category AS (
    SELECT
        event.*,
        category.categoryid,
        category.valid_from_utc AS category_valid_from_utc,
        category.valid_to_utc AS category_valid_to_utc,
        category.is_valid_snapshot AS has_valid_category_snapshot
    FROM core.fct_event AS event
    ASOF LEFT JOIN core.item_category_history AS category
        ON
            event.itemid = category.itemid
            AND event.event_time_utc >= category.valid_from_utc
)

SELECT
    event.*,
    availability.available,
    availability.valid_from_utc AS available_valid_from_utc,
    availability.valid_to_utc AS available_valid_to_utc,
    availability.is_valid_snapshot AS has_valid_available_snapshot
FROM event_with_category AS event
ASOF LEFT JOIN core.item_availability_history AS availability
    ON
        event.itemid = availability.itemid
        AND event.event_time_utc >= availability.valid_from_utc;

CREATE OR REPLACE TABLE core.dim_category AS
WITH RECURSIVE unique_nodes AS (
    SELECT
        categoryid,
        min(parentid) AS parentid
    FROM stg.category_tree
    WHERE categoryid IS NOT NULL
    GROUP BY categoryid
),

rooted AS (
    SELECT
        categoryid,
        parentid,
        categoryid AS root_categoryid,
        0::INTEGER AS depth,
        ('/' || categoryid::VARCHAR || '/')::VARCHAR AS category_path
    FROM unique_nodes
    WHERE parentid IS NULL
    UNION ALL
    SELECT
        child.categoryid,
        child.parentid,
        parent.root_categoryid,
        parent.depth + 1,
        parent.category_path || child.categoryid::VARCHAR || '/'
    FROM unique_nodes AS child
    INNER JOIN rooted AS parent ON child.parentid = parent.categoryid
    WHERE
        parent.depth < 100
        AND strpos(parent.category_path, '/' || child.categoryid::VARCHAR || '/') = 0
),

upward AS (
    SELECT
        categoryid AS origin_categoryid,
        categoryid AS current_categoryid,
        parentid AS next_parentid,
        0::INTEGER AS depth,
        ('/' || categoryid::VARCHAR || '/')::VARCHAR AS visited_path,
        FALSE AS has_cycle
    FROM unique_nodes
    UNION ALL
    SELECT
        upward.origin_categoryid,
        parent.categoryid,
        parent.parentid,
        upward.depth + 1,
        upward.visited_path || parent.categoryid::VARCHAR || '/',
        strpos(
            upward.visited_path,
            '/' || parent.categoryid::VARCHAR || '/'
        ) > 0 AS has_cycle
    FROM upward
    INNER JOIN unique_nodes AS parent
        ON upward.next_parentid = parent.categoryid
    WHERE NOT upward.has_cycle AND upward.depth < 100
),

cycle_flags AS (
    SELECT
        origin_categoryid AS categoryid,
        bool_or(has_cycle) AS has_cycle
    FROM upward
    GROUP BY origin_categoryid
),

duplicate_flags AS (
    SELECT
        categoryid,
        bool_or(is_duplicate_category) AS is_duplicate_category,
        bool_or(is_self_reference) AS is_self_reference
    FROM stg.category_tree
    GROUP BY categoryid
)

SELECT
    nodes.categoryid,
    nodes.parentid,
    rooted.root_categoryid,
    rooted.depth,
    rooted.category_path,
    coalesce(duplicate_flags.is_duplicate_category, FALSE) AS is_duplicate_category,
    coalesce(duplicate_flags.is_self_reference, FALSE) AS is_self_reference,
    coalesce(cycle_flags.has_cycle, FALSE) AS has_cycle,
    rooted.categoryid IS NULL AND NOT coalesce(cycle_flags.has_cycle, FALSE)
        AS has_missing_ancestor,
    rooted.categoryid IS NULL AS is_unreachable
FROM unique_nodes AS nodes
LEFT JOIN rooted USING (categoryid)
LEFT JOIN cycle_flags USING (categoryid)
LEFT JOIN duplicate_flags USING (categoryid);
