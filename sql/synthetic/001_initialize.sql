CREATE SCHEMA IF NOT EXISTS synthetic;

CREATE OR REPLACE TABLE synthetic.experiment_assignment (
    participant_id VARCHAR NOT NULL,
    scenario_id VARCHAR NOT NULL,
    experiment_group VARCHAR NOT NULL,
    exposure_date DATE NOT NULL,
    channel VARCHAR NOT NULL,
    campaign_id VARCHAR NOT NULL,
    was_exposed BOOLEAN NOT NULL,
    was_clicked BOOLEAN NOT NULL,
    was_converted BOOLEAN NOT NULL,
    was_refunded BOOLEAN NOT NULL,
    order_id VARCHAR,
    order_amount DECIMAL(12, 2),
    seed INTEGER NOT NULL,
    data_origin VARCHAR NOT NULL
);

CREATE OR REPLACE TABLE synthetic.channel_daily_input (
    scenario_id VARCHAR NOT NULL,
    activity_date DATE NOT NULL,
    channel VARCHAR NOT NULL,
    campaign_id VARCHAR NOT NULL,
    spend DECIMAL(12, 2) NOT NULL,
    impressions BIGINT NOT NULL,
    clicks BIGINT NOT NULL,
    conversions BIGINT NOT NULL,
    simulated_revenue DECIMAL(14, 2) NOT NULL,
    seed INTEGER NOT NULL,
    data_origin VARCHAR NOT NULL
);
