CREATE OR REPLACE TABLE raw.events AS
SELECT
    row_number() OVER ()::BIGINT AS source_row_number,
    "timestamp"::BIGINT AS "timestamp",
    visitorid::BIGINT AS visitorid,
    event::VARCHAR AS event,
    itemid::BIGINT AS itemid,
    transactionid::BIGINT AS transactionid,
    'events'::VARCHAR AS source_id,
    'events.csv'::VARCHAR AS source_file
FROM read_csv(
    {{ events_csv }},
    header = true,
    auto_detect = false,
    columns = {
        'timestamp': 'BIGINT',
        'visitorid': 'BIGINT',
        'event': 'VARCHAR',
        'itemid': 'BIGINT',
        'transactionid': 'BIGINT'
    },
    nullstr = ''
);

CREATE OR REPLACE TABLE raw.item_properties AS
WITH combined AS (
    SELECT
        row_number() OVER ()::BIGINT AS source_row_number,
        "timestamp"::BIGINT AS "timestamp",
        itemid::BIGINT AS itemid,
        property::VARCHAR AS property,
        value::VARCHAR AS value,
        'item_properties_part1'::VARCHAR AS source_id,
        'item_properties_part1.csv'::VARCHAR AS source_file
    FROM
        read_csv(
            {{ properties_part1_csv }},
            header = true,
            auto_detect = false,
            columns = {
                'timestamp': 'BIGINT',
                'itemid': 'BIGINT',
                'property': 'VARCHAR',
                'value': 'VARCHAR'
            },
            nullstr = ''
        )
    UNION ALL
    SELECT
        row_number() OVER ()::BIGINT AS source_row_number,
        "timestamp"::BIGINT AS "timestamp",
        itemid::BIGINT AS itemid,
        property::VARCHAR AS property,
        value::VARCHAR AS value,
        'item_properties_part2'::VARCHAR AS source_id,
        'item_properties_part2.csv'::VARCHAR AS source_file
    FROM read_csv(
        {{ properties_part2_csv }},
        header = true,
        auto_detect = false,
        columns = {
            'timestamp': 'BIGINT',
            'itemid': 'BIGINT',
            'property': 'VARCHAR',
            'value': 'VARCHAR'
        },
        nullstr = ''
    )
)

SELECT * FROM combined;

CREATE OR REPLACE TABLE raw.category_tree AS
SELECT
    row_number() OVER ()::BIGINT AS source_row_number,
    categoryid::BIGINT AS categoryid,
    parentid::BIGINT AS parentid,
    'category_tree'::VARCHAR AS source_id,
    'category_tree.csv'::VARCHAR AS source_file
FROM read_csv(
    {{ category_tree_csv }},
    header = true,
    auto_detect = false,
    columns = { 'categoryid': 'BIGINT', 'parentid': 'BIGINT' },
    nullstr = ''
);
