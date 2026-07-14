SET TIME ZONE 'UTC';

WITH source_boundary AS (
    SELECT MAX(event_time::timestamptz) AS source_max_time_utc
    FROM makeup_consumer_events.dec
),
cart_input_quality AS (
    SELECT
        COUNT(*)::bigint AS cart_event_rows,
        COUNT(*) FILTER (
            WHERE user_session IS NULL
               OR BTRIM(user_session) = ''
               OR LOWER(BTRIM(user_session)) IN ('nan', 'null', 'none')
               OR product_id IS NULL
        )::bigint
            AS invalid_cart_key_event_rows
    FROM makeup_consumer_events.dec
    WHERE event_type = 'cart'
),
first_cart AS MATERIALIZED (
    SELECT DISTINCT ON (user_session, product_id)
        user_session,
        product_id,
        price,
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
        MIN(e.event_time::timestamptz) AS first_followup_time
    FROM complete_seed s
    LEFT JOIN makeup_consumer_events.dec e
        ON e.user_session = s.user_session
       AND e.product_id = s.product_id
       AND e.event_time::timestamptz > s.first_cart_time
       AND e.event_time::timestamptz <= s.window_end_time
    GROUP BY s.user_session, s.product_id
),
cohort AS MATERIALIZED (
    SELECT
        s.*,
        COALESCE(f.has_purchase_48h, FALSE) AS has_purchase_48h,
        COALESCE(f.has_remove_48h, FALSE) AS has_remove_48h,
        f.first_followup_time,
        CASE
            WHEN COALESCE(f.has_purchase_48h, FALSE) THEN 'A'
            WHEN COALESCE(f.has_remove_48h, FALSE) THEN 'C'
            ELSE 'B'
        END AS group_type
    FROM complete_seed s
    LEFT JOIN followup f
        ON f.user_session = s.user_session
       AND f.product_id = s.product_id
),
duplicate_keys AS (
    SELECT COALESCE(SUM(key_count - 1), 0)::bigint AS duplicate_session_product_excess_rows
    FROM (
        SELECT COUNT(*)::bigint AS key_count
        FROM cohort
        GROUP BY user_session, product_id
        HAVING COUNT(*) > 1
    ) x
)
SELECT
    q.cart_event_rows,
    q.invalid_cart_key_event_rows,
    (SELECT COUNT(*) FROM first_cart)::bigint AS first_observed_cart_rows,
    COUNT(*)::bigint AS complete_48h_rows,
    ((SELECT COUNT(*) FROM first_cart) - COUNT(*))::bigint AS incomplete_tail_rows_excluded,
    MIN(first_cart_time) AS cohort_min_cart_time_utc,
    MAX(first_cart_time) AS cohort_max_cart_time_utc,
    MAX(window_end_time) AS cohort_max_window_end_utc,
    COUNT(*) FILTER (WHERE group_type = 'A')::bigint AS purchase_group_rows,
    COUNT(*) FILTER (WHERE group_type = 'B')::bigint AS unresolved_group_rows,
    COUNT(*) FILTER (WHERE group_type = 'C')::bigint AS remove_group_rows,
    COUNT(*) FILTER (WHERE user_id IS NULL)::bigint AS missing_user_id_rows,
    COUNT(*) FILTER (WHERE brand IS NULL)::bigint AS missing_brand_rows,
    COUNT(*) FILTER (WHERE category_code IS NULL)::bigint AS missing_category_code_rows,
    COUNT(*) FILTER (WHERE price IS NULL)::bigint AS missing_price_rows,
    COUNT(*) FILTER (WHERE price <= 0)::bigint AS nonpositive_price_rows,
    COUNT(*) FILTER (WHERE first_followup_time IS NOT NULL AND first_followup_time <= first_cart_time)::bigint
        AS invalid_followup_order_rows,
    d.duplicate_session_product_excess_rows,
    0::bigint AS inconsistent_label_rows
FROM cohort
CROSS JOIN duplicate_keys d
CROSS JOIN cart_input_quality q
GROUP BY d.duplicate_session_product_excess_rows, q.cart_event_rows, q.invalid_cart_key_event_rows;
