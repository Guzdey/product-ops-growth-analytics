CREATE OR REPLACE TABLE mart.metric_registry AS
WITH origin AS (
    SELECT
        CASE
            WHEN bool_and(data_origin = 'retailrocket') THEN 'real'
            ELSE 'synthetic'
        END AS data_origin
    FROM meta.source_file_manifest
),

definitions (
    metric_id,
    metric_name_cn,
    business_question,
    formula_description,
    grain,
    window_definition,
    limitations
) AS (
    VALUES
    (
        'daily_active_visitors', '日活访客 DAU', '每天有多少活跃访客？',
        '当日去重 visitorid', 'day', 'UTC calendar day',
        '首次出现不等于注册'
    ),
    (
        'rolling_7d_active_visitors', '滚动 7 日活跃访客', '短周期活跃规模如何变化？',
        '当日及前 6 日去重 visitorid', 'day', 'rolling 7 days',
        '观察窗口开始阶段不足完整自然周期'
    ),
    (
        'rolling_30d_active_visitors', '滚动 30 日活跃访客',
        '中周期活跃规模如何变化？', '当日及前 29 日去重 visitorid', 'day',
        'rolling 30 days', '观察窗口开始阶段不足完整自然周期'
    ),
    (
        'dau_mau_stickiness', 'DAU/MAU 活跃粘性', '访客访问频率如何？',
        'DAU / rolling 30-day active visitors', 'day', 'rolling 30 days',
        '不是注册用户口径的产品粘性'
    ),
    (
        'first_observed_visitors', '首次观察访客', '观察窗口内每天出现多少新访客？',
        '首个事件日期等于统计日的去重 visitorid', 'day', 'UTC calendar day',
        '首次观察不等于注册'
    ),
    (
        'returning_visitors', '回访访客', '当日活跃中有多少此前已出现？',
        '当日活跃且首个事件日期早于当日', 'day', 'UTC calendar day',
        '只反映数据观察窗口'
    ),
    (
        'session_count', '会话数', '每天发生多少次访问会话？',
        '30 分钟规则生成的唯一 session_id', 'day', 'UTC calendar day',
        '相邻事件严格大于 30 分钟才开启新会话'
    ),
    (
        'events_per_session', '每会话事件数', '一次访问的交互深度如何？',
        '会话内合格事件数的均值、中位数和 P75', 'day', 'session',
        '排除已标记精确重复和非法事件'
    ),
    (
        'items_per_session', '每会话商品数', '一次访问探索多少不同商品？',
        '会话内去重 itemid 的均值、中位数和 P75', 'day', 'session',
        '无商品数量字段'
    ),
    (
        'session_duration_seconds', '会话时长', '访客一次决策过程持续多久？',
        '最后事件时间减首个事件时间的中位数和 P75', 'day', 'session',
        '单事件会话时长为 0'
    ),
    (
        'behavior_coverage_rate', '行为覆盖率', '多少会话发生过指定行为？',
        '发生指定行为的会话 / 全部合格会话', 'period', 'observation window',
        '描述覆盖，不代表有序转化'
    ),
    (
        'ordered_view_to_cart_rate', '严格浏览到加购率', '浏览后有多少会话继续加购？',
        '严格后于浏览发生加购的会话 / 有浏览会话', 'period', 'session',
        '要求事件时间严格递增'
    ),
    (
        'ordered_cart_to_purchase_rate', '严格加购到购买率',
        '有效加购后有多少会话购买？',
        '严格后于有效加购发生交易的会话 / 有有效加购会话',
        'period', 'session', '交易数仍需按 transactionid 去重'
    ),
    (
        'ordered_view_to_purchase_rate', '严格浏览到购买率',
        '浏览后有多少会话最终购买？',
        '严格后于浏览发生交易的会话 / 有浏览会话', 'period', 'session',
        '不要求中间必须加购'
    ),
    (
        'same_item_funnel_rate', '同商品严格漏斗', '排除跨商品混合后转化如何？',
        '同 session_id + itemid 内严格有序步骤转化', 'period', 'session_item',
        '分母是会话商品组合'
    ),
    (
        'cart_abandonment_rate', '购物车放弃率', '加购后未购买的会话占比多少？',
        '加购后无更晚交易的会话 / 有加购会话', 'period', 'session',
        '不能识别站外购买'
    ),
    (
        'median_step_latency', '漏斗步骤耗时', '步骤之间通常需要多久？',
        '严格匹配步骤时间差的中位数和 P75', 'period', 'session',
        '只包含完成对应步骤的会话'
    ),
    (
        'retention_d1', 'D1 活跃留存', '首日后第 1 天是否回来？',
        'D1 活跃访客 / 可完整观察 D1 的 Cohort 访客', 'cohort', '1 day',
        '排除右截断 Cohort'
    ),
    (
        'retention_d3', 'D3 活跃留存', '首日后第 3 天是否回来？',
        'D3 活跃访客 / 可完整观察 D3 的 Cohort 访客', 'cohort', '3 days',
        '排除右截断 Cohort'
    ),
    (
        'retention_d7', 'D7 活跃留存', '首日后第 7 天是否回来？',
        'D7 活跃访客 / 可完整观察 D7 的 Cohort 访客', 'cohort', '7 days',
        '排除右截断 Cohort'
    ),
    (
        'retention_d14', 'D14 活跃留存', '首日后第 14 天是否回来？',
        'D14 活跃访客 / 可完整观察 D14 的 Cohort 访客', 'cohort', '14 days',
        '排除右截断 Cohort'
    ),
    (
        'retention_d30', 'D30 活跃留存', '首日后第 30 天是否回来？',
        'D30 活跃访客 / 可完整观察 D30 的 Cohort 访客', 'cohort', '30 days',
        '受数据观察窗口长度限制'
    ),
    (
        'purchasing_visitor_rate', '购买访客率', '活跃访客中有多少发生购买？',
        '有交易的去重访客 / 活跃去重访客', 'period', 'observation window',
        '没有金额字段'
    ),
    (
        'transaction_count', '唯一交易数', '观察窗口内有多少订单代理记录？',
        'COUNT(DISTINCT transactionid)', 'day_period', 'observation window',
        '不等于交易事件行数'
    ),
    (
        'distinct_items_per_transaction', '每交易不同商品数',
        '一个交易包含多少不同商品？',
        '每个 transactionid 的去重 itemid，汇总均值、中位数和 P75',
        'transaction', 'observation window', '不能推断购买数量'
    ),
    (
        'repeat_purchase_visitor_rate', '复购访客率', '购买访客中多少发生至少两次交易？',
        '至少 2 个唯一交易的访客 / 至少 1 个唯一交易的访客',
        'period', 'observation window', '只覆盖数据观察窗口'
    ),
    (
        'repurchase_interval_days', '复购间隔', '二次购买触达时机如何？',
        '同访客相邻唯一交易时间差的中位数和 P75', 'visitor',
        'observation window', '左右边界可能截断间隔'
    ),
    (
        'category_session_conversion_rate', '品类会话转化率',
        '品类浏览会话中多少发生同品类交易？',
        '同品类有浏览且有交易的会话 / 品类浏览会话', 'category',
        'observation window', '属性按事件时点关联'
    ),
    (
        'category_opportunity_score', '品类机会规模', '哪些高流量品类转化低于同级？',
        '浏览会话数 × max(0, 同级转化中位数 - 当前转化率)', 'category',
        'observation window', '理论排序分，不等于可实现新增交易'
    ),
    (
        'item_property_coverage_rate', '可解释属性覆盖率',
        '事件时点能关联多少有效商品属性？',
        '关联有效 categoryid 或 available 的事件 / 合格事件', 'period',
        'observation window', '匿名属性不做业务解释'
    ),
    (
        'category_linkage_rate', '分类树关联率', '有效商品分类能否连接分类树？',
        '分类可连接 dim_category 的事件 / 有有效 categoryid 的事件', 'period',
        'observation window', '属性按事件时点关联'
    )
)

SELECT
    definitions.metric_id,
    definitions.metric_name_cn,
    definitions.business_question,
    definitions.formula_description,
    definitions.grain,
    definitions.window_definition,
    origin.data_origin,
    definitions.limitations,
    'validated' AS status
FROM definitions
CROSS JOIN origin;

CREATE OR REPLACE TABLE mart.visitor_daily_activity AS
WITH origin AS (
    SELECT
        CASE
            WHEN bool_and(data_origin = 'retailrocket') THEN 'real'
            ELSE 'synthetic'
        END AS data_origin
    FROM meta.source_file_manifest
)

SELECT
    cast(event.event_time_utc AS DATE) AS activity_date,
    event.visitorid,
    count(*) AS event_count,
    count(DISTINCT event.itemid) AS distinct_item_count,
    bool_or(event.event = 'view') AS has_view,
    bool_or(event.event = 'addtocart') AS has_addtocart,
    bool_or(event.event = 'transaction') AS has_transaction,
    count(DISTINCT event.transactionid) FILTER (
        WHERE event.event = 'transaction'
    ) AS distinct_transaction_count,
    origin.data_origin
FROM core.fct_event AS event
CROSS JOIN origin
WHERE
    NOT event.is_exact_duplicate
    AND NOT event.is_unknown_event
    AND NOT event.has_required_null
    AND NOT event.has_transaction_id_mismatch
GROUP BY activity_date, event.visitorid, origin.data_origin;

CREATE OR REPLACE TABLE mart.session_metrics AS
WITH origin AS (
    SELECT
        CASE
            WHEN bool_and(data_origin = 'retailrocket') THEN 'real'
            ELSE 'synthetic'
        END AS data_origin
    FROM meta.source_file_manifest
)

SELECT
    event.session_id,
    event.visitorid,
    event.visitor_session_number,
    min(event.event_time_utc) AS session_start_utc,
    max(event.event_time_utc) AS session_end_utc,
    date_diff(
        'second', min(event.event_time_utc), max(event.event_time_utc)
    ) AS session_duration_seconds,
    count(*) AS event_count,
    count(DISTINCT event.itemid) AS distinct_item_count,
    count(*) FILTER (WHERE event.event = 'view') AS view_event_count,
    count(*) FILTER (WHERE event.event = 'addtocart') AS addtocart_event_count,
    count(*) FILTER (WHERE event.event = 'transaction') AS transaction_event_count,
    count(DISTINCT event.transactionid) FILTER (
        WHERE event.event = 'transaction'
    ) AS distinct_transaction_count,
    origin.data_origin
FROM core.fct_event AS event
CROSS JOIN origin
WHERE
    NOT event.is_exact_duplicate
    AND NOT event.is_unknown_event
    AND NOT event.has_required_null
    AND NOT event.has_transaction_id_mismatch
GROUP BY
    event.session_id,
    event.visitorid,
    event.visitor_session_number,
    origin.data_origin;

CREATE OR REPLACE TABLE mart.daily_activity AS
WITH bounds AS (
    SELECT
        min(activity_date) AS min_date,
        max(activity_date) AS max_date
    FROM mart.visitor_daily_activity
),

calendar AS (
    SELECT
        cast(unnest(generate_series(min_date, max_date, INTERVAL 1 DAY)) AS DATE)
            AS activity_date
    FROM bounds
),

daily AS (
    SELECT
        activity_date,
        count(*) AS daily_active_visitors,
        count(*) FILTER (WHERE has_view) AS viewing_visitors,
        count(*) FILTER (WHERE has_addtocart) AS carting_visitors,
        count(*) FILTER (WHERE has_transaction) AS purchasing_visitors
    FROM mart.visitor_daily_activity
    GROUP BY activity_date
),

first_seen AS (
    SELECT
        visitorid,
        min(activity_date) AS first_activity_date
    FROM mart.visitor_daily_activity
    GROUP BY visitorid
),

first_seen_daily AS (
    SELECT
        first_activity_date AS activity_date,
        count(*) AS first_observed_visitors
    FROM first_seen
    GROUP BY first_activity_date
),

rolling AS (
    SELECT
        calendar.activity_date,
        count(DISTINCT activity.visitorid) FILTER (
            WHERE
            activity.activity_date
            >= calendar.activity_date - INTERVAL 6 DAY
        ) AS rolling_7d_active_visitors,
        count(DISTINCT activity.visitorid) AS rolling_30d_active_visitors
    FROM calendar
    LEFT JOIN mart.visitor_daily_activity AS activity
        ON
            activity.activity_date
            BETWEEN calendar.activity_date - INTERVAL 29 DAY
            AND calendar.activity_date
    GROUP BY calendar.activity_date
)

SELECT
    calendar.activity_date,
    coalesce(daily.daily_active_visitors, 0) AS daily_active_visitors,
    rolling.rolling_7d_active_visitors,
    rolling.rolling_30d_active_visitors,
    coalesce(first_seen_daily.first_observed_visitors, 0) AS first_observed_visitors,
    coalesce(daily.daily_active_visitors, 0)
    - coalesce(first_seen_daily.first_observed_visitors, 0) AS returning_visitors,
    coalesce(daily.viewing_visitors, 0) AS viewing_visitors,
    coalesce(daily.carting_visitors, 0) AS carting_visitors,
    coalesce(daily.purchasing_visitors, 0) AS purchasing_visitors,
    coalesce(
        cast(daily.daily_active_visitors AS DOUBLE)
        / nullif(rolling.rolling_30d_active_visitors, 0),
        0
    ) AS dau_mau_stickiness,
    coalesce(
        cast(daily.purchasing_visitors AS DOUBLE)
        / nullif(daily.daily_active_visitors, 0),
        0
    ) AS purchasing_visitor_rate,
    coalesce(
        (
            SELECT min(activity_origin.data_origin)
            FROM mart.visitor_daily_activity AS activity_origin
        ),
        'unknown'
    ) AS data_origin
FROM calendar
LEFT JOIN daily USING (activity_date)
LEFT JOIN first_seen_daily USING (activity_date)
LEFT JOIN rolling USING (activity_date)
ORDER BY calendar.activity_date;

CREATE OR REPLACE TABLE mart.daily_session_metrics AS
SELECT
    cast(session_start_utc AS DATE) AS activity_date,
    count(*) AS session_count,
    count(DISTINCT visitorid) AS active_visitors,
    avg(event_count) AS average_events_per_session,
    median(event_count) AS median_events_per_session,
    quantile_cont(event_count, 0.75) AS p75_events_per_session,
    avg(distinct_item_count) AS average_items_per_session,
    median(distinct_item_count) AS median_items_per_session,
    quantile_cont(distinct_item_count, 0.75) AS p75_items_per_session,
    avg(session_duration_seconds) AS average_session_duration_seconds,
    median(session_duration_seconds) AS median_session_duration_seconds,
    quantile_cont(session_duration_seconds, 0.75)
        AS p75_session_duration_seconds,
    min(data_origin) AS data_origin
FROM mart.session_metrics
GROUP BY activity_date
ORDER BY activity_date;
