CREATE OR REPLACE TABLE mart.item_performance AS
WITH item_category AS (
    SELECT
        itemid,
        mode(categoryid) AS primary_observed_categoryid
    FROM core.fct_event_item_context
    WHERE
        categoryid IS NOT NULL
        AND NOT is_exact_duplicate
        AND NOT is_unknown_event
        AND NOT has_required_null
        AND NOT has_transaction_id_mismatch
    GROUP BY itemid
)

SELECT
    funnel.itemid,
    category.primary_observed_categoryid AS categoryid,
    count(*) FILTER (WHERE funnel.has_view) AS view_session_count,
    count(*) FILTER (WHERE funnel.has_cart) AS cart_session_count,
    count(*) FILTER (WHERE funnel.has_transaction) AS transaction_session_count,
    count(*) FILTER (WHERE funnel.has_ordered_cart) AS ordered_cart_session_count,
    count(*) FILTER (WHERE funnel.has_ordered_full_funnel)
        AS ordered_purchase_session_count,
    count(*) FILTER (WHERE funnel.has_ordered_cart)::DOUBLE
    / nullif(count(*) FILTER (WHERE funnel.has_view), 0)
        AS ordered_view_to_cart_rate,
    count(*) FILTER (WHERE funnel.has_ordered_full_funnel)::DOUBLE
    / nullif(count(*) FILTER (WHERE funnel.has_ordered_cart), 0)
        AS ordered_cart_to_purchase_rate,
    min(funnel.data_origin) AS data_origin
FROM mart.session_item_funnel AS funnel
LEFT JOIN item_category AS category USING (itemid)
GROUP BY funnel.itemid, category.primary_observed_categoryid;

CREATE OR REPLACE TABLE mart.category_session_funnel AS
WITH eligible_event AS (
    SELECT *
    FROM core.fct_event_item_context
    WHERE
        categoryid IS NOT NULL
        AND NOT is_exact_duplicate
        AND NOT is_unknown_event
        AND NOT has_required_null
        AND NOT has_transaction_id_mismatch
)

SELECT
    session_id,
    min(visitorid) AS visitorid,
    categoryid,
    bool_or(event = 'view') AS has_view,
    bool_or(event = 'addtocart') AS has_cart,
    bool_or(event = 'transaction') AS has_transaction,
    count(DISTINCT transactionid) FILTER (WHERE event = 'transaction')
        AS distinct_transaction_count,
    (
        SELECT min(session_origin.data_origin)
        FROM mart.session_metrics AS session_origin
    ) AS data_origin
FROM eligible_event
GROUP BY session_id, categoryid;

CREATE OR REPLACE TABLE mart.category_performance AS
WITH category_base AS (
    SELECT
        funnel.categoryid,
        category.parentid,
        category.root_categoryid,
        category.depth,
        count(*) FILTER (WHERE funnel.has_view) AS view_session_count,
        count(*) FILTER (WHERE funnel.has_cart) AS cart_session_count,
        count(*) FILTER (WHERE funnel.has_view AND funnel.has_transaction)
            AS converted_session_count,
        count(DISTINCT funnel.visitorid) FILTER (WHERE funnel.has_view)
            AS viewing_visitor_count,
        sum(funnel.distinct_transaction_count) AS distinct_transaction_count,
        count(*) FILTER (WHERE funnel.has_view AND funnel.has_transaction)::DOUBLE
        / nullif(count(*) FILTER (WHERE funnel.has_view), 0)
            AS session_conversion_rate,
        min(funnel.data_origin) AS data_origin
    FROM mart.category_session_funnel AS funnel
    INNER JOIN core.dim_category AS category USING (categoryid)
    GROUP BY
        funnel.categoryid,
        category.parentid,
        category.root_categoryid,
        category.depth
),

peer_benchmark AS (
    SELECT
        *,
        median(
            CASE WHEN view_session_count >= 200 THEN session_conversion_rate END
        ) OVER (PARTITION BY parentid) AS sibling_conversion_median,
        count(*) FILTER (WHERE view_session_count >= 200)
            OVER (PARTITION BY parentid) AS eligible_sibling_count
    FROM category_base
),

wilson AS (
    SELECT
        *,
        1.959963984540054 AS z_value,
        1 + pow(1.959963984540054, 2) / nullif(view_session_count, 0)
            AS wilson_denominator
    FROM peer_benchmark
)

SELECT
    categoryid,
    parentid,
    root_categoryid,
    depth,
    view_session_count,
    cart_session_count,
    converted_session_count,
    viewing_visitor_count,
    distinct_transaction_count,
    session_conversion_rate,
    CASE
        WHEN converted_session_count = 0 THEN 0
        ELSE greatest(0, (
            session_conversion_rate
            + pow(z_value, 2) / (2 * nullif(view_session_count, 0))
            - z_value * sqrt(
                session_conversion_rate * (1 - session_conversion_rate)
                / nullif(view_session_count, 0)
                + pow(z_value, 2) / (4 * pow(nullif(view_session_count, 0), 2))
            )
        ) / wilson_denominator)
    END AS conversion_wilson_low_95,
    CASE
        WHEN converted_session_count = view_session_count THEN 1
        ELSE least(1, (
            session_conversion_rate
            + pow(z_value, 2) / (2 * nullif(view_session_count, 0))
            + z_value * sqrt(
                session_conversion_rate * (1 - session_conversion_rate)
                / nullif(view_session_count, 0)
                + pow(z_value, 2) / (4 * pow(nullif(view_session_count, 0), 2))
            )
        ) / wilson_denominator)
    END AS conversion_wilson_high_95,
    sibling_conversion_median,
    sibling_conversion_median - session_conversion_rate AS sibling_conversion_gap,
    view_session_count
    * greatest(0, sibling_conversion_median - session_conversion_rate)
        AS category_opportunity_score,
    view_session_count >= 200 AS meets_sample_threshold,
    view_session_count >= 200
    AND eligible_sibling_count >= 2
    AND sibling_conversion_median - session_conversion_rate >= 0.02
        AS is_opportunity_candidate,
    eligible_sibling_count,
    data_origin
FROM wilson;

CREATE OR REPLACE TABLE mart.data_quality_summary AS
WITH event_context AS (
    SELECT *
    FROM core.fct_event_item_context
    WHERE
        NOT is_exact_duplicate
        AND NOT is_unknown_event
        AND NOT has_required_null
        AND NOT has_transaction_id_mismatch
),

eligible_counts AS (
    SELECT
        count(*) AS eligible_event_count,
        count(*) FILTER (WHERE has_valid_category_snapshot)
            AS category_property_event_count,
        count(*) FILTER (WHERE has_valid_available_snapshot)
            AS availability_property_event_count,
        count(*) FILTER (
            WHERE has_valid_category_snapshot OR has_valid_available_snapshot
        ) AS interpretable_property_event_count
    FROM event_context
),

category_linkage AS (
    SELECT
        count(*) AS category_event_count,
        count(*) FILTER (WHERE category.categoryid IS NOT NULL)
            AS linked_category_event_count
    FROM event_context AS event
    LEFT JOIN core.dim_category AS category USING (categoryid)
    WHERE event.categoryid IS NOT NULL
),

metrics AS (
    SELECT
        'item_category_property_coverage_rate' AS metric_id,
        category_property_event_count AS numerator_count,
        eligible_event_count AS denominator_count
    FROM eligible_counts
    UNION ALL
    SELECT
        'item_availability_property_coverage_rate',
        availability_property_event_count,
        eligible_event_count
    FROM eligible_counts
    UNION ALL
    SELECT
        'item_property_coverage_rate',
        interpretable_property_event_count,
        eligible_event_count
    FROM eligible_counts
    UNION ALL
    SELECT
        'category_linkage_rate',
        linked_category_event_count,
        category_event_count
    FROM category_linkage
    UNION ALL
    SELECT
        'excluded_exact_duplicate_event_rate',
        count(*) FILTER (WHERE is_exact_duplicate),
        count(*)
    FROM core.fct_event
    UNION ALL
    SELECT
        'excluded_invalid_event_rate',
        count(*) FILTER (
            WHERE is_unknown_event OR has_required_null OR has_transaction_id_mismatch
        ),
        count(*)
    FROM core.fct_event
)

SELECT
    metric_id,
    numerator_count,
    denominator_count,
    numerator_count::DOUBLE / nullif(denominator_count, 0) AS metric_rate,
    (
        SELECT min(session_origin.data_origin)
        FROM mart.session_metrics AS session_origin
    ) AS data_origin
FROM metrics;
