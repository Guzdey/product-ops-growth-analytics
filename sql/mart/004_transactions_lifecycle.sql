CREATE OR REPLACE TABLE mart.transaction_metrics AS
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
WHERE
    event = 'transaction'
    AND transactionid IS NOT NULL
    AND NOT is_exact_duplicate
    AND NOT is_unknown_event
    AND NOT has_required_null
    AND NOT has_transaction_id_mismatch
GROUP BY transactionid;

CREATE OR REPLACE TABLE mart.visitor_transaction_summary AS
WITH transaction_stats AS (
    SELECT
        visitorid,
        count(*) AS transaction_count,
        min(transaction_time_utc) AS first_transaction_time_utc,
        max(transaction_time_utc) AS last_transaction_time_utc,
        sum(distinct_item_count) AS summed_distinct_items
    FROM mart.transaction_metrics
    WHERE NOT has_multiple_visitors
    GROUP BY visitorid
)

SELECT
    cohort.visitorid,
    coalesce(transaction.transaction_count, 0) AS transaction_count,
    transaction.first_transaction_time_utc,
    transaction.last_transaction_time_utc,
    coalesce(transaction.summed_distinct_items, 0) AS summed_distinct_items,
    cohort.data_origin
FROM mart.visitor_cohort AS cohort
LEFT JOIN transaction_stats AS transaction USING (visitorid);

CREATE OR REPLACE TABLE mart.visitor_repurchase_interval AS
WITH ordered_transaction AS (
    SELECT
        visitorid,
        transactionid,
        transaction_time_utc,
        lag(transaction_time_utc) OVER (
            PARTITION BY visitorid ORDER BY transaction_time_utc, transactionid
        ) AS previous_transaction_time_utc
    FROM mart.transaction_metrics
    WHERE NOT has_multiple_visitors
)

SELECT
    visitorid,
    transactionid,
    transaction_time_utc,
    previous_transaction_time_utc,
    date_diff(
        'second', previous_transaction_time_utc, transaction_time_utc
    )::DOUBLE / 86400 AS repurchase_interval_days,
    (
        SELECT min(cohort_origin.data_origin)
        FROM mart.visitor_cohort AS cohort_origin
    ) AS data_origin
FROM ordered_transaction
WHERE previous_transaction_time_utc IS NOT NULL;

CREATE OR REPLACE TABLE mart.transaction_daily AS
WITH event_rows AS (
    SELECT
        event_time_utc::DATE AS transaction_date,
        count(*) AS transaction_event_count
    FROM core.fct_event
    WHERE
        event = 'transaction'
        AND transactionid IS NOT NULL
        AND NOT is_exact_duplicate
        AND NOT is_unknown_event
        AND NOT has_required_null
        AND NOT has_transaction_id_mismatch
    GROUP BY transaction_date
)

SELECT
    (transaction.transaction_time_utc)::DATE AS transaction_date,
    count(*) AS transaction_count,
    count(DISTINCT transaction.visitorid) AS purchasing_visitors,
    coalesce(min(event_rows.transaction_event_count), 0) AS transaction_event_count,
    avg(transaction.distinct_item_count) AS average_distinct_items_per_transaction,
    median(transaction.distinct_item_count) AS median_distinct_items_per_transaction,
    quantile_cont(transaction.distinct_item_count, 0.75)
        AS p75_distinct_items_per_transaction,
    (
        SELECT min(cohort_origin.data_origin)
        FROM mart.visitor_cohort AS cohort_origin
    ) AS data_origin
FROM mart.transaction_metrics AS transaction
LEFT JOIN event_rows
    ON (transaction.transaction_time_utc)::DATE = event_rows.transaction_date
WHERE NOT transaction.has_multiple_visitors
GROUP BY (transaction.transaction_time_utc)::DATE
ORDER BY transaction_date;

CREATE OR REPLACE TABLE mart.transaction_summary AS
WITH visitor AS (
    SELECT
        count(*) AS active_visitor_count,
        count(*) FILTER (WHERE transaction_count >= 1) AS purchasing_visitor_count,
        count(*) FILTER (WHERE transaction_count >= 2) AS repeat_purchase_visitor_count
    FROM mart.visitor_transaction_summary
),

transaction_stats AS (
    SELECT
        count(*) AS transaction_count,
        sum(transaction_event_count) AS transaction_event_count,
        avg(distinct_item_count) AS average_distinct_items_per_transaction,
        median(distinct_item_count) AS median_distinct_items_per_transaction,
        quantile_cont(distinct_item_count, 0.75)
            AS p75_distinct_items_per_transaction
    FROM mart.transaction_metrics
    WHERE NOT has_multiple_visitors
),

interval_stats AS (
    SELECT
        count(*) AS repurchase_interval_count,
        median(repurchase_interval_days) AS median_repurchase_interval_days,
        quantile_cont(repurchase_interval_days, 0.75) AS p75_repurchase_interval_days
    FROM mart.visitor_repurchase_interval
)

SELECT
    visitor.active_visitor_count,
    visitor.purchasing_visitor_count,
    visitor.purchasing_visitor_count::DOUBLE
    / nullif(visitor.active_visitor_count, 0) AS purchasing_visitor_rate,
    visitor.repeat_purchase_visitor_count,
    visitor.repeat_purchase_visitor_count::DOUBLE
    / nullif(visitor.purchasing_visitor_count, 0) AS repeat_purchase_visitor_rate,
    transaction_stats.transaction_count,
    transaction_stats.transaction_event_count,
    transaction_stats.average_distinct_items_per_transaction,
    transaction_stats.median_distinct_items_per_transaction,
    transaction_stats.p75_distinct_items_per_transaction,
    interval_stats.repurchase_interval_count,
    interval_stats.median_repurchase_interval_days,
    interval_stats.p75_repurchase_interval_days,
    (
        SELECT min(cohort_origin.data_origin)
        FROM mart.visitor_cohort AS cohort_origin
    ) AS data_origin
FROM visitor
CROSS JOIN transaction_stats
CROSS JOIN interval_stats;

CREATE OR REPLACE TABLE mart.lifecycle_threshold AS
WITH ordered_session AS (
    SELECT
        visitorid,
        session_start_utc,
        lag(session_start_utc) OVER (
            PARTITION BY visitorid ORDER BY session_start_utc, session_id
        ) AS previous_session_start_utc
    FROM mart.session_metrics
),

gap_stats AS (
    SELECT
        quantile_cont(
            date_diff('second', previous_session_start_utc, session_start_utc)::DOUBLE
            / 86400,
            0.75
        ) AS p75_return_gap_days
    FROM ordered_session
    WHERE previous_session_start_utc IS NOT NULL
)

SELECT
    p75_return_gap_days,
    greatest(7, ceil(coalesce(p75_return_gap_days, 30)))::INTEGER
        AS at_risk_threshold_days,
    (
        SELECT max(activity.activity_date)
        FROM mart.visitor_daily_activity AS activity
    )
        AS observation_end_date,
    (
        SELECT min(cohort_origin.data_origin)
        FROM mart.visitor_cohort AS cohort_origin
    ) AS data_origin
FROM gap_stats;

CREATE OR REPLACE TABLE mart.visitor_lifecycle AS
WITH behavior AS (
    SELECT
        visitorid,
        count(*) AS session_count,
        sum(view_event_count) AS view_event_count,
        sum(addtocart_event_count) AS addtocart_event_count,
        bool_or(addtocart_event_count > 0) AS has_addtocart
    FROM mart.session_metrics
    GROUP BY visitorid
),

profile AS (
    SELECT
        cohort.visitorid,
        cohort.cohort_date,
        cohort.last_activity_date,
        cohort.active_day_count,
        behavior.session_count,
        behavior.view_event_count,
        behavior.addtocart_event_count,
        behavior.has_addtocart,
        transaction.transaction_count,
        threshold.at_risk_threshold_days,
        threshold.observation_end_date,
        cohort.data_origin
    FROM mart.visitor_cohort AS cohort
    INNER JOIN behavior USING (visitorid)
    INNER JOIN mart.visitor_transaction_summary AS transaction USING (visitorid)
    CROSS JOIN mart.lifecycle_threshold AS threshold
)

SELECT
    visitorid,
    cohort_date,
    last_activity_date,
    active_day_count,
    session_count,
    view_event_count,
    addtocart_event_count,
    transaction_count,
    CASE
        WHEN transaction_count >= 2 THEN 'repeat_buyer'
        WHEN transaction_count = 1 THEN 'first_time_buyer'
        WHEN has_addtocart THEN 'cart_no_purchase'
        WHEN session_count >= 2 THEN 'active_browser'
        ELSE 'first_session_bounce'
    END AS lifecycle_segment,
    (
        session_count >= 2 OR transaction_count >= 1
    )
    AND last_activity_date
    <= observation_end_date - at_risk_threshold_days AS is_at_risk,
    at_risk_threshold_days,
    data_origin
FROM profile;

CREATE OR REPLACE TABLE mart.lifecycle_segment_summary AS
SELECT
    lifecycle_segment,
    count(*) AS visitor_count,
    count(*) FILTER (WHERE is_at_risk) AS at_risk_visitor_count,
    count(*)::DOUBLE / sum(count(*)) OVER () AS visitor_share,
    min(at_risk_threshold_days) AS at_risk_threshold_days,
    min(data_origin) AS data_origin
FROM mart.visitor_lifecycle
GROUP BY lifecycle_segment
ORDER BY visitor_count DESC, lifecycle_segment ASC;
