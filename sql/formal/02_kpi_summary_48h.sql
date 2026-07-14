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
        BOOL_OR(e.event_type = 'remove_from_cart') AS has_remove_48h
    FROM complete_seed s
    LEFT JOIN makeup_consumer_events.dec e
        ON e.user_session = s.user_session
       AND e.product_id = s.product_id
       AND e.event_time::timestamptz > s.first_cart_time
       AND e.event_time::timestamptz <= s.window_end_time
       AND e.event_type IN ('purchase', 'remove_from_cart')
    GROUP BY s.user_session, s.product_id
),
cohort AS MATERIALIZED (
    SELECT
        s.*,
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
counts AS (
    SELECT
        COUNT(*)::bigint AS cohort_count,
        COUNT(*) FILTER (WHERE group_type = 'A')::bigint AS purchase_count,
        COUNT(*) FILTER (WHERE group_type = 'B')::bigint AS unresolved_count,
        COUNT(*) FILTER (WHERE group_type = 'C')::bigint AS remove_count,
        COUNT(DISTINCT user_id)::bigint AS distinct_users,
        COUNT(DISTINCT user_session)::bigint AS distinct_sessions,
        COUNT(DISTINCT product_id)::bigint AS distinct_products,
        COUNT(DISTINCT brand)::bigint AS distinct_known_brands,
        COUNT(*) FILTER (WHERE brand IS NOT NULL)::bigint AS known_brand_rows
    FROM cohort
)
SELECT
    *,
    ROUND(100.0 * purchase_count / NULLIF(cohort_count, 0), 4) AS purchase_rate_pct,
    ROUND(100.0 * unresolved_count / NULLIF(cohort_count, 0), 4) AS unresolved_rate_pct,
    ROUND(100.0 * remove_count / NULLIF(cohort_count, 0), 4) AS remove_rate_pct,
    ROUND(100.0 * purchase_count / NULLIF(purchase_count + remove_count, 0), 4) AS clear_purchase_rate_pct,
    ROUND(remove_count::numeric / NULLIF(purchase_count, 0), 4) AS remove_to_purchase_ratio,
    ROUND(100.0 * known_brand_rows / NULLIF(cohort_count, 0), 4) AS known_brand_coverage_pct
FROM counts;
