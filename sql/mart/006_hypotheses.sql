CREATE OR REPLACE TABLE mart.hypothesis_results AS
WITH h1_groups AS (
    SELECT
        max(retained_visitor_count) FILTER (
            WHERE first_session_segment = 'cart_no_purchase' AND day_n = 7
        ) AS cart_retained,
        max(eligible_visitor_count) FILTER (
            WHERE first_session_segment = 'cart_no_purchase' AND day_n = 7
        ) AS cart_eligible,
        max(retained_visitor_count) FILTER (
            WHERE first_session_segment = 'browse_only' AND day_n = 7
        ) AS browse_retained,
        max(eligible_visitor_count) FILTER (
            WHERE first_session_segment = 'browse_only' AND day_n = 7
        ) AS browse_eligible,
        min(data_origin) AS data_origin
    FROM mart.retention_summary
),

h1 AS (
    SELECT
        'H1' AS hypothesis_id,
        '首次会话加购未购访客的 D7 留存率比仅浏览访客高至少 5 个百分点'
            AS hypothesis_cn,
        'retention_d7_segment_difference' AS metric_id,
        cart_retained::DOUBLE / nullif(cart_eligible, 0)
        - browse_retained::DOUBLE / nullif(browse_eligible, 0) AS observed_effect,
        0.05 AS threshold,
        '>=' AS comparison_operator,
        coalesce(
            cart_retained::DOUBLE / nullif(cart_eligible, 0)
            - browse_retained::DOUBLE / nullif(browse_eligible, 0) >= 0.05,
            FALSE
        ) AS is_supported,
        cart_retained AS primary_success_count,
        cart_eligible AS primary_group_count,
        browse_retained AS comparison_success_count,
        browse_eligible AS comparison_group_count,
        NULL::DOUBLE AS confidence_low_95,
        NULL::DOUBLE AS confidence_high_95,
        NULL::DOUBLE AS p_value,
        'D7 仅纳入可完整观察 Cohort；差异按访客数加权'
            AS evidence_summary,
        data_origin
    FROM h1_groups
),

h2_counts AS (
    SELECT
        max(denominator_count) FILTER (
            WHERE
            metric_id = 'ordered_view_to_cart_rate'
            AND funnel_scope = 'session'
        ) AS view_sessions,
        max(numerator_count) FILTER (
            WHERE
            metric_id = 'ordered_view_to_cart_rate'
            AND funnel_scope = 'session'
        ) AS ordered_cart_sessions,
        max(numerator_count) FILTER (
            WHERE
            metric_id = 'ordered_cart_to_purchase_rate'
            AND funnel_scope = 'session'
        ) AS purchased_sessions,
        min(data_origin) AS data_origin
    FROM mart.funnel_summary
),

h2 AS (
    SELECT
        'H2' AS hypothesis_id,
        '严格有序漏斗中存在一个步骤贡献超过 60% 的流失会话'
            AS hypothesis_cn,
        'largest_ordered_funnel_loss_share' AS metric_id,
        greatest(
            view_sessions - ordered_cart_sessions,
            ordered_cart_sessions - purchased_sessions
        )::DOUBLE / nullif(view_sessions - purchased_sessions, 0)
            AS observed_effect,
        0.60 AS threshold,
        '>' AS comparison_operator,
        coalesce(
            greatest(
                view_sessions - ordered_cart_sessions,
                ordered_cart_sessions - purchased_sessions
            )::DOUBLE / nullif(view_sessions - purchased_sessions, 0) > 0.60,
            FALSE
        ) AS is_supported,
        greatest(
            view_sessions - ordered_cart_sessions,
            ordered_cart_sessions - purchased_sessions
        ) AS primary_success_count,
        view_sessions - purchased_sessions AS primary_group_count,
        NULL::BIGINT AS comparison_success_count,
        NULL::BIGINT AS comparison_group_count,
        NULL::DOUBLE AS confidence_low_95,
        NULL::DOUBLE AS confidence_high_95,
        NULL::DOUBLE AS p_value,
        '两步流失分别为浏览到加购、加购到购买，并除以严格漏斗总流失'
            AS evidence_summary,
        data_origin
    FROM h2_counts
),

h3_candidate AS (
    SELECT *
    FROM mart.category_performance
    WHERE meets_sample_threshold
    ORDER BY sibling_conversion_gap DESC NULLS LAST, view_session_count DESC
    LIMIT 1
),

h3 AS (
    SELECT
        'H3' AS hypothesis_id,
        '至少一个高流量品类的转化率比同级基准低至少 2 个百分点'
            AS hypothesis_cn,
        'maximum_category_sibling_conversion_gap' AS metric_id,
        candidate.sibling_conversion_gap AS observed_effect,
        0.02 AS threshold,
        '>=' AS comparison_operator,
        coalesce(candidate.sibling_conversion_gap >= 0.02, FALSE) AS is_supported,
        candidate.converted_session_count AS primary_success_count,
        candidate.view_session_count AS primary_group_count,
        NULL::BIGINT AS comparison_success_count,
        NULL::BIGINT AS comparison_group_count,
        candidate.conversion_wilson_low_95 AS confidence_low_95,
        candidate.conversion_wilson_high_95 AS confidence_high_95,
        NULL::DOUBLE AS p_value,
        coalesce(
            '最高合格品类 categoryid=' || candidate.categoryid::VARCHAR
            || '；基准为同父级合格品类转化中位数',
            '没有品类达到 200 个浏览会话门槛'
        ) AS evidence_summary,
        coalesce(
            candidate.data_origin,
            (
                SELECT min(session_origin.data_origin)
                FROM mart.session_metrics AS session_origin
            )
        ) AS data_origin
    FROM (SELECT 1 AS placeholder) AS anchor
    LEFT JOIN h3_candidate AS candidate ON TRUE
    WHERE anchor.placeholder = 1
)

SELECT * FROM h1
UNION ALL
SELECT * FROM h2
UNION ALL
SELECT * FROM h3;
