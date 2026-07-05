DROP TABLE IF EXISTS makeup_consumer_events."11_user_behavior_groups_window_48h";

CREATE TABLE makeup_consumer_events."11_user_behavior_groups_window_48h" AS
WITH first_cart AS (
    SELECT DISTINCT ON (user_session, product_id)
        user_session,
        product_id,
        event_type,
        price,
        user_id,
        brand,
        category_code,
        category_id,
        event_time::timestamptz AS first_cart_time,
        event_time::timestamptz + INTERVAL '48 hours' AS window_end_time
    FROM makeup_consumer_events.dec
    WHERE event_type = 'cart'
    ORDER BY user_session, product_id, event_time::timestamptz
),
cohort AS (
    SELECT *
    FROM first_cart
    WHERE first_cart_time < TIMESTAMPTZ '2019-12-30 00:00:00+00'
),
followup AS (
    SELECT
        c.user_session,
        c.product_id,
        BOOL_OR(e.event_type = 'purchase') AS has_purchase_48h,
        BOOL_OR(e.event_type = 'remove_from_cart') AS has_remove_48h,
        COALESCE(
            TO_JSONB(ARRAY_AGG(DISTINCT e.event_type) FILTER (WHERE e.event_type IS NOT NULL))::text,
            '[]'
        ) AS event_type_window,
        MIN(e.event_time::timestamptz) AS first_followup_time
    FROM cohort c
    LEFT JOIN makeup_consumer_events.dec e
        ON e.user_session = c.user_session
       AND e.product_id = c.product_id
       AND e.event_time::timestamptz > c.first_cart_time
       AND e.event_time::timestamptz <= c.window_end_time
    GROUP BY c.user_session, c.product_id
)
SELECT
    c.user_session,
    c.product_id,
    c.event_type,
    c.price,
    c.user_id,
    c.brand,
    c.category_code,
    c.category_id,
    c.first_cart_time AS event_time,
    CASE
        WHEN COALESCE(f.has_purchase_48h, FALSE) THEN 'A'
        WHEN COALESCE(f.has_remove_48h, FALSE) THEN 'C'
        ELSE 'B'
    END AS group_type,
    c.first_cart_time,
    c.window_end_time,
    COALESCE(f.has_purchase_48h, FALSE) AS has_purchase_48h,
    COALESCE(f.has_remove_48h, FALSE) AS has_remove_48h,
    COALESCE(f.event_type_window, '[]') AS event_type_window,
    f.first_followup_time
FROM cohort c
LEFT JOIN followup f
    ON f.user_session = c.user_session
   AND f.product_id = c.product_id;

CREATE INDEX IF NOT EXISTS idx_11_window_48h_group_type
    ON makeup_consumer_events."11_user_behavior_groups_window_48h" (group_type);

CREATE INDEX IF NOT EXISTS idx_11_window_48h_brand_group
    ON makeup_consumer_events."11_user_behavior_groups_window_48h" (brand, group_type);

CREATE INDEX IF NOT EXISTS idx_11_window_48h_first_cart_time
    ON makeup_consumer_events."11_user_behavior_groups_window_48h" (first_cart_time);
