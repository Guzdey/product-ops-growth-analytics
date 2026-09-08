CREATE OR REPLACE TABLE synthetic.metric_registry AS
SELECT
    definitions.metric_id,
    definitions.metric_name_cn,
    definitions.formula,
    definitions.grain,
    definitions.data_origin
FROM (
    VALUES
    ('ctr', '点击率', 'clicks / impressions', 'channel_day', 'synthetic'),
    ('click_cvr', '点击后转化率', 'conversions / clicks', 'channel_day', 'synthetic'),
    ('assignment_cvr', '分组用户转化率', 'converted / assigned', 'experiment_arm', 'synthetic'),
    ('cac', '获客成本', 'spend / conversions', 'channel_day', 'synthetic'),
    ('roas', '广告支出回报', 'simulated_revenue / spend', 'channel_day', 'synthetic'),
    ('simulated_gmv', '模拟成交金额', 'sum(order_amount)', 'channel_day', 'synthetic'),
    ('simulated_aov', '模拟客单价', 'simulated_revenue / conversions', 'channel_day', 'synthetic'),
    ('refund_rate', '退款率护栏', 'refunded / converted', 'experiment_arm', 'synthetic')
) AS definitions (metric_id, metric_name_cn, formula, grain, data_origin);

CREATE OR REPLACE TABLE synthetic.experiment_arm_metrics AS
SELECT
    scenario_id,
    experiment_group,
    count(*) AS assigned_users,
    count(*) FILTER (WHERE was_exposed) AS exposed_users,
    count(*) FILTER (WHERE was_clicked) AS clicked_users,
    count(*) FILTER (WHERE was_converted) AS converted_users,
    count(*) FILTER (WHERE was_refunded) AS refunded_users,
    sum(order_amount) FILTER (WHERE was_converted) AS simulated_gmv,
    count(DISTINCT order_id) FILTER (WHERE was_converted) AS simulated_orders,
    converted_users::DOUBLE / nullif(assigned_users, 0) AS assignment_cvr,
    clicked_users::DOUBLE / nullif(exposed_users, 0) AS ctr,
    converted_users::DOUBLE / nullif(clicked_users, 0) AS click_cvr,
    simulated_gmv::DOUBLE / nullif(simulated_orders, 0) AS simulated_aov,
    refunded_users::DOUBLE / nullif(converted_users, 0) AS refund_rate,
    min(seed) AS seed,
    'synthetic' AS data_origin
FROM synthetic.experiment_assignment
GROUP BY scenario_id, experiment_group;

CREATE OR REPLACE TABLE synthetic.channel_daily_metrics AS
SELECT
    scenario_id,
    activity_date,
    channel,
    campaign_id,
    spend,
    impressions,
    clicks,
    conversions,
    simulated_revenue AS simulated_gmv,
    clicks::DOUBLE / nullif(impressions, 0) AS ctr,
    conversions::DOUBLE / nullif(clicks, 0) AS click_cvr,
    spend::DOUBLE / nullif(conversions, 0) AS cac,
    simulated_revenue::DOUBLE / nullif(spend, 0) AS roas,
    simulated_revenue::DOUBLE / nullif(conversions, 0) AS simulated_aov,
    seed,
    'synthetic' AS data_origin
FROM synthetic.channel_daily_input;

CREATE OR REPLACE TABLE synthetic.channel_summary AS
SELECT
    scenario_id,
    channel,
    sum(spend) AS spend,
    sum(impressions) AS impressions,
    sum(clicks) AS clicks,
    sum(conversions) AS conversions,
    sum(simulated_gmv) AS simulated_gmv,
    sum(clicks)::DOUBLE / nullif(sum(impressions), 0) AS ctr,
    sum(conversions)::DOUBLE / nullif(sum(clicks), 0) AS click_cvr,
    sum(spend)::DOUBLE / nullif(sum(conversions), 0) AS cac,
    sum(simulated_gmv)::DOUBLE / nullif(sum(spend), 0) AS roas,
    sum(simulated_gmv)::DOUBLE / nullif(sum(conversions), 0) AS simulated_aov,
    min(seed) AS seed,
    'synthetic' AS data_origin
FROM synthetic.channel_daily_metrics
GROUP BY scenario_id, channel;

CREATE OR REPLACE TABLE synthetic.guardrail_summary AS
SELECT
    scenario_id,
    experiment_group,
    converted_users,
    refunded_users,
    refund_rate,
    0.01::DOUBLE AS maximum_allowed_increase,
    seed,
    'synthetic' AS data_origin
FROM synthetic.experiment_arm_metrics;
