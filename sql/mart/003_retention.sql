CREATE OR REPLACE TABLE mart.visitor_cohort AS
WITH visitor_activity AS (
    SELECT
        visitorid,
        min(activity_date) AS first_activity_date,
        max(activity_date) AS last_activity_date,
        count(*) AS active_day_count,
        sum(event_count) AS event_count
    FROM mart.visitor_daily_activity
    GROUP BY visitorid
),

ranked_session AS (
    SELECT
        session_id,
        visitorid,
        session_start_utc,
        row_number() OVER (
            PARTITION BY visitorid ORDER BY session_start_utc, session_id
        ) AS session_rank
    FROM mart.session_metrics
),

first_session AS (
    SELECT
        ranked_session.visitorid,
        ranked_session.session_id AS first_session_id,
        funnel.has_view,
        funnel.has_cart,
        funnel.has_transaction
    FROM ranked_session
    INNER JOIN mart.session_funnel AS funnel USING (session_id, visitorid)
    WHERE ranked_session.session_rank = 1
)

SELECT
    activity.visitorid,
    activity.first_activity_date AS cohort_date,
    activity.last_activity_date,
    activity.active_day_count,
    activity.event_count,
    first_session.first_session_id,
    CASE
        WHEN first_session.has_transaction THEN 'first_session_purchase'
        WHEN first_session.has_cart THEN 'cart_no_purchase'
        ELSE 'browse_only'
    END AS first_session_segment,
    (
        SELECT min(activity_origin.data_origin)
        FROM mart.visitor_daily_activity AS activity_origin
    ) AS data_origin
FROM visitor_activity AS activity
INNER JOIN first_session USING (visitorid);

CREATE OR REPLACE TABLE mart.retention_cohort_daily AS
WITH horizons (day_n) AS (
    VALUES (1), (3), (7), (14), (30)
),

observation AS (
    SELECT max(activity_date) AS observation_end_date
    FROM mart.visitor_daily_activity
),

visitor_horizon AS (
    SELECT
        cohort.visitorid,
        cohort.cohort_date,
        cohort.first_session_segment,
        horizons.day_n,
        cohort.cohort_date + horizons.day_n AS target_date,
        cohort.cohort_date + horizons.day_n <= observation.observation_end_date
            AS is_eligible,
        activity.visitorid IS NOT NULL AS is_retained,
        cohort.data_origin
    FROM mart.visitor_cohort AS cohort
    CROSS JOIN horizons
    CROSS JOIN observation
    LEFT JOIN mart.visitor_daily_activity AS activity
        ON
            cohort.visitorid = activity.visitorid
            AND activity.activity_date = cohort.cohort_date + horizons.day_n
),

segment_cohort AS (
    SELECT
        cohort_date,
        first_session_segment,
        day_n,
        min(target_date) AS target_date,
        bool_and(is_eligible) AS is_eligible,
        count(*) AS cohort_size,
        CASE
            WHEN bool_and(is_eligible)
                THEN count(*) FILTER (WHERE is_retained)
        END AS retained_visitors,
        min(data_origin) AS data_origin
    FROM visitor_horizon
    GROUP BY cohort_date, first_session_segment, day_n
),

all_cohort AS (
    SELECT
        cohort_date,
        'all' AS first_session_segment,
        day_n,
        min(target_date) AS target_date,
        bool_and(is_eligible) AS is_eligible,
        count(*) AS cohort_size,
        CASE
            WHEN bool_and(is_eligible)
                THEN count(*) FILTER (WHERE is_retained)
        END AS retained_visitors,
        min(data_origin) AS data_origin
    FROM visitor_horizon
    GROUP BY cohort_date, day_n
),

combined AS (
    SELECT * FROM segment_cohort
    UNION ALL
    SELECT * FROM all_cohort
)

SELECT
    cohort_date,
    first_session_segment,
    day_n,
    target_date,
    is_eligible,
    cohort_size,
    retained_visitors,
    CASE
        WHEN is_eligible
            THEN retained_visitors::DOUBLE / nullif(cohort_size, 0)
    END AS retention_rate,
    data_origin
FROM combined
ORDER BY cohort_date, first_session_segment, day_n;

CREATE OR REPLACE TABLE mart.retention_summary AS
SELECT
    first_session_segment,
    day_n,
    count(*) AS eligible_cohort_count,
    sum(cohort_size) AS eligible_visitor_count,
    sum(retained_visitors) AS retained_visitor_count,
    sum(retained_visitors)::DOUBLE / nullif(sum(cohort_size), 0)
        AS weighted_retention_rate,
    min(data_origin) AS data_origin
FROM mart.retention_cohort_daily
WHERE is_eligible
GROUP BY first_session_segment, day_n
ORDER BY first_session_segment, day_n;

CREATE OR REPLACE TABLE mart.retention_cohort_weekly AS
WITH horizons AS (
    SELECT range AS week_number
    FROM range(0, 13)
),

visitor_week AS (
    SELECT DISTINCT
        visitorid,
        date_trunc('week', activity_date)::DATE AS activity_week
    FROM mart.visitor_daily_activity
),

cohort AS (
    SELECT
        visitorid,
        date_trunc('week', cohort_date)::DATE AS cohort_week,
        data_origin
    FROM mart.visitor_cohort
),

observation AS (
    SELECT max(activity_date) AS observation_end_date
    FROM mart.visitor_daily_activity
),

cohort_sizes AS (
    SELECT
        cohort_week,
        count(*) AS cohort_size,
        min(data_origin) AS data_origin
    FROM cohort
    GROUP BY cohort_week
),

retained AS (
    SELECT
        cohort.cohort_week,
        date_diff('week', cohort.cohort_week, activity.activity_week) AS week_number,
        count(DISTINCT cohort.visitorid) AS retained_visitors
    FROM cohort
    INNER JOIN visitor_week AS activity USING (visitorid)
    WHERE activity.activity_week >= cohort.cohort_week
    GROUP BY cohort.cohort_week, week_number
)

SELECT
    sizes.cohort_week,
    horizons.week_number,
    sizes.cohort_size,
    coalesce(retained.retained_visitors, 0) AS retained_visitors,
    coalesce(retained.retained_visitors, 0)::DOUBLE
    / nullif(sizes.cohort_size, 0) AS retention_rate,
    sizes.data_origin
FROM cohort_sizes AS sizes
CROSS JOIN horizons
CROSS JOIN observation
LEFT JOIN retained USING (cohort_week, week_number)
WHERE
    sizes.cohort_week
    + ((horizons.week_number + 1) * INTERVAL 7 DAY)
    - INTERVAL 1 DAY <= observation.observation_end_date
ORDER BY sizes.cohort_week, horizons.week_number;
