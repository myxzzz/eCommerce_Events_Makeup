SET TIME ZONE 'UTC';

WITH source_boundary AS (
    SELECT MAX(event_time::timestamptz) AS source_max_time_utc
    FROM makeup_consumer_events.dec
),
first_cart AS MATERIALIZED (
    SELECT DISTINCT ON (user_session, product_id)
        user_session,
        product_id,
        user_id,
        CASE
            WHEN brand IS NULL OR BTRIM(brand) = '' OR LOWER(BTRIM(brand)) IN ('nan', 'null', 'none') THEN NULL
            ELSE BTRIM(brand)
        END AS brand,
        CASE
            WHEN category_code IS NULL
              OR BTRIM(category_code) = ''
              OR LOWER(BTRIM(category_code)) IN ('nan', 'null', 'none') THEN NULL
            ELSE BTRIM(category_code)
        END AS category_code,
        category_id,
        price,
        event_time::timestamptz AS first_cart_time,
        event_time::timestamptz + INTERVAL '48 hours' AS window_end_time
    FROM makeup_consumer_events.dec
    WHERE event_type = 'cart'
      AND user_session IS NOT NULL
      AND BTRIM(user_session) <> ''
      AND LOWER(BTRIM(user_session)) NOT IN ('nan', 'null', 'none')
      AND product_id IS NOT NULL
    ORDER BY user_session, product_id, event_time::timestamptz
),
complete_seed AS MATERIALIZED (
    SELECT f.*
    FROM first_cart f
    CROSS JOIN source_boundary b
    WHERE f.window_end_time <= b.source_max_time_utc
),
followup AS MATERIALIZED (
    SELECT
        s.user_session,
        s.product_id,
        BOOL_OR(e.event_type = 'purchase') AS has_purchase_48h,
        BOOL_OR(e.event_type = 'remove_from_cart') AS has_remove_48h,
        MIN(e.event_time::timestamptz) AS first_followup_time,
        MIN(e.event_time::timestamptz) FILTER (WHERE e.event_type = 'purchase') AS first_purchase_time,
        MIN(e.event_time::timestamptz) FILTER (WHERE e.event_type = 'remove_from_cart') AS first_remove_time
    FROM complete_seed s
    LEFT JOIN makeup_consumer_events.dec e
        ON e.user_session = s.user_session
       AND e.product_id = s.product_id
       AND e.event_time::timestamptz > s.first_cart_time
       AND e.event_time::timestamptz <= s.window_end_time
    GROUP BY s.user_session, s.product_id
)
SELECT
    s.user_session,
    s.product_id,
    s.user_id,
    s.brand,
    s.category_code,
    s.category_id,
    s.price,
    s.first_cart_time,
    s.window_end_time,
    CASE
        WHEN COALESCE(f.has_purchase_48h, FALSE) THEN 'A'
        WHEN COALESCE(f.has_remove_48h, FALSE) THEN 'C'
        ELSE 'B'
    END AS group_type,
    COALESCE(f.has_purchase_48h, FALSE) AS has_purchase_48h,
    COALESCE(f.has_remove_48h, FALSE) AS has_remove_48h,
    f.first_followup_time,
    f.first_purchase_time,
    f.first_remove_time
FROM complete_seed s
LEFT JOIN followup f
    ON f.user_session = s.user_session
   AND f.product_id = s.product_id
ORDER BY s.first_cart_time, s.user_session, s.product_id;
