-- Rebuild the original A/B/C grouped table in SQL.
--
-- Original project grain:
-- one row = user_session + product_id in December, after keeping the first
-- event of each event_type among cart / purchase / remove_from_cart.
--
-- Group rule:
-- A = purchase appears in the event list
-- C = no purchase, but remove_from_cart appears
-- B = cart only / no clear purchase or remove result
--
-- Note:
-- This is the original full-month event-result口径. It does not enforce a fixed
-- post-cart observation window. Use 07_build_11_user_behavior_groups_window_48h.sql
-- when studying the stricter 48-hour cohort口径.

DROP TABLE IF EXISTS makeup_consumer_events."03_user_behavior_groups_sql";

CREATE TABLE makeup_consumer_events."03_user_behavior_groups_sql" AS
WITH base_events AS (
    SELECT
        user_session,
        product_id,
        price,
        event_type,
        event_time::timestamptz AS event_time,
        user_id,
        brand,
        category_code,
        category_id,
        ROW_NUMBER() OVER (
            PARTITION BY user_session, product_id, event_type
            ORDER BY event_time::timestamptz
        ) AS rn
    FROM makeup_consumer_events.dec
    WHERE event_type IN ('cart', 'purchase', 'remove_from_cart')
),
first_event_per_type AS (
    SELECT *
    FROM base_events
    WHERE rn = 1
),
grouped AS (
    SELECT
        user_session,
        product_id,
        ARRAY_AGG(event_type ORDER BY event_time) AS event_type,
        (ARRAY_AGG(price ORDER BY event_time))[1] AS price,
        (ARRAY_AGG(user_id ORDER BY event_time))[1] AS user_id,
        (ARRAY_AGG(brand ORDER BY event_time))[1] AS brand,
        (ARRAY_AGG(category_code ORDER BY event_time))[1] AS category_code,
        (ARRAY_AGG(category_id ORDER BY event_time))[1] AS category_id,
        MIN(event_time) AS event_time,
        BOOL_OR(event_type = 'purchase') AS has_purchase,
        BOOL_OR(event_type = 'remove_from_cart') AS has_remove
    FROM first_event_per_type
    GROUP BY user_session, product_id
)
SELECT
    user_session,
    product_id,
    event_type,
    price,
    user_id,
    brand,
    category_code,
    category_id,
    event_time,
    CASE
        WHEN has_purchase THEN 'A'
        WHEN has_remove THEN 'C'
        ELSE 'B'
    END AS group_type
FROM grouped;

-- Quick check.
SELECT
    group_type,
    COUNT(*) AS row_count
FROM makeup_consumer_events."03_user_behavior_groups_sql"
GROUP BY group_type
ORDER BY group_type;

