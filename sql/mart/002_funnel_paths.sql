CREATE OR REPLACE TABLE mart.session_funnel AS
WITH eligible_event AS (
    SELECT *
    FROM core.fct_event
    WHERE
        NOT is_exact_duplicate
        AND NOT is_unknown_event
        AND NOT has_required_null
        AND NOT has_transaction_id_mismatch
),

first_steps AS (
    SELECT
        session_id,
        min(visitorid) AS visitorid,
        min(event_time_utc) FILTER (WHERE event = 'view') AS first_view_time_utc,
        min(event_time_utc) FILTER (WHERE event = 'addtocart') AS first_cart_time_utc,
        min(event_time_utc) FILTER (WHERE event = 'transaction')
            AS first_transaction_time_utc
    FROM eligible_event
    GROUP BY session_id
),

ordered_cart AS (
    SELECT
        event.session_id,
        min(event.event_time_utc) AS ordered_cart_time_utc
    FROM eligible_event AS event
    INNER JOIN first_steps USING (session_id)
    WHERE
        event.event = 'addtocart'
        AND event.event_time_utc > first_steps.first_view_time_utc
    GROUP BY event.session_id
),

ordered_transaction_from_view AS (
    SELECT
        event.session_id,
        min(event.event_time_utc) AS ordered_view_transaction_time_utc
    FROM eligible_event AS event
    INNER JOIN first_steps USING (session_id)
    WHERE
        event.event = 'transaction'
        AND event.event_time_utc > first_steps.first_view_time_utc
    GROUP BY event.session_id
),

ordered_transaction_from_cart AS (
    SELECT
        event.session_id,
        min(event.event_time_utc) AS ordered_cart_transaction_time_utc
    FROM eligible_event AS event
    INNER JOIN ordered_cart USING (session_id)
    WHERE
        event.event = 'transaction'
        AND event.event_time_utc > ordered_cart.ordered_cart_time_utc
    GROUP BY event.session_id
),

transaction_after_any_cart AS (
    SELECT
        event.session_id,
        min(event.event_time_utc) AS transaction_after_any_cart_time_utc
    FROM eligible_event AS event
    INNER JOIN first_steps USING (session_id)
    WHERE
        event.event = 'transaction'
        AND event.event_time_utc > first_steps.first_cart_time_utc
    GROUP BY event.session_id
)

SELECT
    session.session_id,
    session.visitorid,
    session.session_start_utc,
    first_steps.first_view_time_utc,
    first_steps.first_cart_time_utc,
    first_steps.first_transaction_time_utc,
    ordered_cart.ordered_cart_time_utc,
    ordered_transaction_from_view.ordered_view_transaction_time_utc,
    ordered_transaction_from_cart.ordered_cart_transaction_time_utc,
    first_steps.first_view_time_utc IS NOT NULL AS has_view,
    first_steps.first_cart_time_utc IS NOT NULL AS has_cart,
    first_steps.first_transaction_time_utc IS NOT NULL AS has_transaction,
    ordered_cart.ordered_cart_time_utc IS NOT NULL AS has_ordered_cart,
    ordered_transaction_from_view.ordered_view_transaction_time_utc IS NOT NULL
        AS has_ordered_view_purchase,
    ordered_transaction_from_cart.ordered_cart_transaction_time_utc IS NOT NULL
        AS has_ordered_full_funnel,
    first_steps.first_cart_time_utc IS NOT NULL
    AND transaction_after_any_cart.transaction_after_any_cart_time_utc IS NULL
        AS is_cart_abandoned,
    session.data_origin
FROM mart.session_metrics AS session
INNER JOIN first_steps USING (session_id)
LEFT JOIN ordered_cart USING (session_id)
LEFT JOIN ordered_transaction_from_view USING (session_id)
LEFT JOIN ordered_transaction_from_cart USING (session_id)
LEFT JOIN transaction_after_any_cart USING (session_id);

CREATE OR REPLACE TABLE mart.session_item_funnel AS
WITH eligible_event AS (
    SELECT *
    FROM core.fct_event
    WHERE
        NOT is_exact_duplicate
        AND NOT is_unknown_event
        AND NOT has_required_null
        AND NOT has_transaction_id_mismatch
),

first_steps AS (
    SELECT
        session_id,
        itemid,
        min(visitorid) AS visitorid,
        min(event_time_utc) FILTER (WHERE event = 'view') AS first_view_time_utc,
        min(event_time_utc) FILTER (WHERE event = 'addtocart') AS first_cart_time_utc,
        min(event_time_utc) FILTER (WHERE event = 'transaction')
            AS first_transaction_time_utc
    FROM eligible_event
    GROUP BY session_id, itemid
),

ordered_cart AS (
    SELECT
        event.session_id,
        event.itemid,
        min(event.event_time_utc) AS ordered_cart_time_utc
    FROM eligible_event AS event
    INNER JOIN first_steps USING (session_id, itemid)
    WHERE
        event.event = 'addtocart'
        AND event.event_time_utc > first_steps.first_view_time_utc
    GROUP BY event.session_id, event.itemid
),

ordered_transaction_from_view AS (
    SELECT
        event.session_id,
        event.itemid,
        min(event.event_time_utc) AS ordered_view_transaction_time_utc
    FROM eligible_event AS event
    INNER JOIN first_steps USING (session_id, itemid)
    WHERE
        event.event = 'transaction'
        AND event.event_time_utc > first_steps.first_view_time_utc
    GROUP BY event.session_id, event.itemid
),

ordered_transaction_from_cart AS (
    SELECT
        event.session_id,
        event.itemid,
        min(event.event_time_utc) AS ordered_cart_transaction_time_utc
    FROM eligible_event AS event
    INNER JOIN ordered_cart USING (session_id, itemid)
    WHERE
        event.event = 'transaction'
        AND event.event_time_utc > ordered_cart.ordered_cart_time_utc
    GROUP BY event.session_id, event.itemid
)

SELECT
    first_steps.session_id,
    first_steps.visitorid,
    first_steps.itemid,
    first_steps.first_view_time_utc,
    first_steps.first_cart_time_utc,
    first_steps.first_transaction_time_utc,
    ordered_cart.ordered_cart_time_utc,
    ordered_transaction_from_view.ordered_view_transaction_time_utc,
    ordered_transaction_from_cart.ordered_cart_transaction_time_utc,
    first_steps.first_view_time_utc IS NOT NULL AS has_view,
    first_steps.first_cart_time_utc IS NOT NULL AS has_cart,
    first_steps.first_transaction_time_utc IS NOT NULL AS has_transaction,
    ordered_cart.ordered_cart_time_utc IS NOT NULL AS has_ordered_cart,
    ordered_transaction_from_view.ordered_view_transaction_time_utc IS NOT NULL
        AS has_ordered_view_purchase,
    ordered_transaction_from_cart.ordered_cart_transaction_time_utc IS NOT NULL
        AS has_ordered_full_funnel,
    (
        SELECT min(session_origin.data_origin)
        FROM mart.session_metrics AS session_origin
    ) AS data_origin
FROM first_steps
LEFT JOIN ordered_cart USING (session_id, itemid)
LEFT JOIN ordered_transaction_from_view USING (session_id, itemid)
LEFT JOIN ordered_transaction_from_cart USING (session_id, itemid);

CREATE OR REPLACE TABLE mart.funnel_summary AS
WITH session_counts AS (
    SELECT
        count(*) AS total_count,
        count(*) FILTER (WHERE has_view) AS view_count,
        count(*) FILTER (WHERE has_cart) AS cart_count,
        count(*) FILTER (WHERE has_transaction) AS transaction_count,
        count(*) FILTER (WHERE has_ordered_cart) AS ordered_cart_count,
        count(*) FILTER (WHERE has_ordered_view_purchase)
            AS ordered_view_purchase_count,
        count(*) FILTER (WHERE has_ordered_full_funnel)
            AS ordered_full_funnel_count,
        count(*) FILTER (WHERE is_cart_abandoned) AS cart_abandoned_count,
        min(data_origin) AS data_origin
    FROM mart.session_funnel
),

item_counts AS (
    SELECT
        count(*) FILTER (WHERE has_view) AS view_count,
        count(*) FILTER (WHERE has_ordered_cart) AS ordered_cart_count,
        count(*) FILTER (WHERE has_ordered_view_purchase)
            AS ordered_view_purchase_count,
        count(*) FILTER (WHERE has_ordered_full_funnel)
            AS ordered_full_funnel_count,
        min(data_origin) AS data_origin
    FROM mart.session_item_funnel
),

metrics AS (
    SELECT
        'behavior_view_coverage' AS metric_id,
        'session' AS funnel_scope,
        view_count AS numerator_count,
        total_count AS denominator_count,
        data_origin
    FROM session_counts
    UNION ALL
    SELECT
        'behavior_cart_coverage',
        'session',
        cart_count,
        total_count,
        data_origin
    FROM session_counts
    UNION ALL
    SELECT
        'behavior_transaction_coverage',
        'session',
        transaction_count,
        total_count,
        data_origin
    FROM session_counts
    UNION ALL
    SELECT
        'ordered_view_to_cart_rate',
        'session',
        ordered_cart_count,
        view_count,
        data_origin
    FROM session_counts
    UNION ALL
    SELECT
        'ordered_cart_to_purchase_rate',
        'session',
        ordered_full_funnel_count,
        ordered_cart_count,
        data_origin
    FROM session_counts
    UNION ALL
    SELECT
        'ordered_view_to_purchase_rate',
        'session',
        ordered_view_purchase_count,
        view_count,
        data_origin
    FROM session_counts
    UNION ALL
    SELECT
        'cart_abandonment_rate',
        'session',
        cart_abandoned_count,
        cart_count,
        data_origin
    FROM session_counts
    UNION ALL
    SELECT
        'ordered_view_to_cart_rate',
        'same_item_session',
        ordered_cart_count,
        view_count,
        data_origin
    FROM item_counts
    UNION ALL
    SELECT
        'ordered_cart_to_purchase_rate',
        'same_item_session',
        ordered_full_funnel_count,
        ordered_cart_count,
        data_origin
    FROM item_counts
    UNION ALL
    SELECT
        'ordered_view_to_purchase_rate',
        'same_item_session',
        ordered_view_purchase_count,
        view_count,
        data_origin
    FROM item_counts
)

SELECT
    metric_id,
    funnel_scope,
    numerator_count,
    denominator_count,
    numerator_count::DOUBLE / nullif(denominator_count, 0) AS metric_rate,
    denominator_count - numerator_count AS dropoff_count,
    data_origin
FROM metrics;

CREATE OR REPLACE TABLE mart.funnel_latency_summary AS
WITH latencies AS (
    SELECT
        'view_to_cart' AS funnel_step,
        date_diff('second', first_view_time_utc, ordered_cart_time_utc)
            AS latency_seconds,
        data_origin
    FROM mart.session_funnel
    WHERE ordered_cart_time_utc IS NOT NULL
    UNION ALL
    SELECT
        'cart_to_transaction',
        date_diff(
            'second', ordered_cart_time_utc, ordered_cart_transaction_time_utc
        ),
        data_origin
    FROM mart.session_funnel
    WHERE ordered_cart_transaction_time_utc IS NOT NULL
    UNION ALL
    SELECT
        'view_to_transaction',
        date_diff(
            'second', first_view_time_utc, ordered_view_transaction_time_utc
        ),
        data_origin
    FROM mart.session_funnel
    WHERE ordered_view_transaction_time_utc IS NOT NULL
)

SELECT
    funnel_step,
    count(*) AS matched_session_count,
    median(latency_seconds) AS median_latency_seconds,
    quantile_cont(latency_seconds, 0.75) AS p75_latency_seconds,
    min(data_origin) AS data_origin
FROM latencies
GROUP BY funnel_step;

CREATE OR REPLACE TABLE mart.session_path_summary AS
WITH eligible_event AS (
    SELECT *
    FROM core.fct_event
    WHERE
        NOT is_exact_duplicate
        AND NOT is_unknown_event
        AND NOT has_required_null
        AND NOT has_transaction_id_mismatch
),

session_path AS (
    SELECT
        session_id,
        min(visitorid) AS visitorid,
        string_agg(event, ' > ' ORDER BY event_timestamp_ms, event_id) AS event_path,
        count(*) AS event_count,
        count(DISTINCT transactionid) AS distinct_transaction_count
    FROM eligible_event
    GROUP BY session_id
)

SELECT
    event_path,
    count(*) AS session_count,
    count(DISTINCT visitorid) AS visitor_count,
    sum(distinct_transaction_count) AS distinct_transaction_count,
    median(event_count) AS median_event_count,
    count(*)::DOUBLE / sum(count(*)) OVER () AS session_share,
    (
        SELECT min(session_origin.data_origin)
        FROM mart.session_metrics AS session_origin
    ) AS data_origin
FROM session_path
GROUP BY event_path
ORDER BY session_count DESC, event_path ASC;

CREATE OR REPLACE TABLE mart.funnel_anomaly_summary AS
WITH metrics AS (
    SELECT
        'transaction_without_prior_view_session' AS anomaly_id,
        count(*) FILTER (WHERE has_transaction AND NOT has_ordered_view_purchase)
            AS anomaly_count,
        count(*) FILTER (WHERE has_transaction) AS reference_count,
        min(data_origin) AS data_origin
    FROM mart.session_funnel
    UNION ALL
    SELECT
        'transaction_without_prior_cart_session',
        count(*) FILTER (WHERE has_transaction AND NOT has_ordered_full_funnel),
        count(*) FILTER (WHERE has_transaction),
        min(data_origin)
    FROM mart.session_funnel
    UNION ALL
    SELECT
        'cart_without_prior_view_session',
        count(*) FILTER (WHERE has_cart AND NOT has_ordered_cart),
        count(*) FILTER (WHERE has_cart),
        min(data_origin)
    FROM mart.session_funnel
)

SELECT
    anomaly_id,
    anomaly_count,
    reference_count,
    anomaly_count::DOUBLE / nullif(reference_count, 0) AS anomaly_rate,
    data_origin
FROM metrics;
