SET TIME ZONE 'UTC';

WITH source_boundary AS (
    SELECT MAX(event_time::timestamptz) AS source_max_time_utc
    FROM makeup_consumer_events.dec
),
first_cart AS MATERIALIZED (
    SELECT DISTINCT ON (user_session, product_id)
        user_session,
        product_id,
        event_time::timestamptz AS first_cart_time
    FROM makeup_consumer_events.dec
    WHERE event_type = 'cart'
      AND user_session IS NOT NULL
      AND BTRIM(user_session) <> ''
      AND LOWER(BTRIM(user_session)) NOT IN ('nan', 'null', 'none')
      AND product_id IS NOT NULL
    ORDER BY user_session, product_id, event_time::timestamptz
),
seed AS MATERIALIZED (
    SELECT f.*
    FROM first_cart f
    CROSS JOIN source_boundary b
    WHERE f.first_cart_time + INTERVAL '72 hours' <= b.source_max_time_utc
),
followup AS MATERIALIZED (
    SELECT
        s.user_session,
        s.product_id,
        BOOL_OR(e.event_type = 'purchase' AND e.event_time::timestamptz <= s.first_cart_time + INTERVAL '24 hours') AS purchase_24h,
        BOOL_OR(e.event_type = 'remove_from_cart' AND e.event_time::timestamptz <= s.first_cart_time + INTERVAL '24 hours') AS remove_24h,
        BOOL_OR(e.event_type = 'purchase' AND e.event_time::timestamptz <= s.first_cart_time + INTERVAL '48 hours') AS purchase_48h,
        BOOL_OR(e.event_type = 'remove_from_cart' AND e.event_time::timestamptz <= s.first_cart_time + INTERVAL '48 hours') AS remove_48h,
        BOOL_OR(e.event_type = 'purchase') AS purchase_72h,
        BOOL_OR(e.event_type = 'remove_from_cart') AS remove_72h
    FROM seed s
    LEFT JOIN makeup_consumer_events.dec e
        ON e.user_session = s.user_session
       AND e.product_id = s.product_id
       AND e.event_time::timestamptz > s.first_cart_time
       AND e.event_time::timestamptz <= s.first_cart_time + INTERVAL '72 hours'
       AND e.event_type IN ('purchase', 'remove_from_cart')
    GROUP BY s.user_session, s.product_id
),
window_counts AS (
    SELECT
        24 AS window_hours,
        COUNT(*)::bigint AS common_cohort_count,
        COUNT(*) FILTER (WHERE COALESCE(purchase_24h, FALSE))::bigint AS purchase_count,
        COUNT(*) FILTER (
            WHERE NOT COALESCE(purchase_24h, FALSE) AND NOT COALESCE(remove_24h, FALSE)
        )::bigint AS unresolved_count,
        COUNT(*) FILTER (
            WHERE NOT COALESCE(purchase_24h, FALSE) AND COALESCE(remove_24h, FALSE)
        )::bigint AS remove_count
    FROM followup
    UNION ALL
    SELECT
        48,
        COUNT(*)::bigint,
        COUNT(*) FILTER (WHERE COALESCE(purchase_48h, FALSE))::bigint,
        COUNT(*) FILTER (
            WHERE NOT COALESCE(purchase_48h, FALSE) AND NOT COALESCE(remove_48h, FALSE)
        )::bigint,
        COUNT(*) FILTER (
            WHERE NOT COALESCE(purchase_48h, FALSE) AND COALESCE(remove_48h, FALSE)
        )::bigint
    FROM followup
    UNION ALL
    SELECT
        72,
        COUNT(*)::bigint,
        COUNT(*) FILTER (WHERE COALESCE(purchase_72h, FALSE))::bigint,
        COUNT(*) FILTER (
            WHERE NOT COALESCE(purchase_72h, FALSE) AND NOT COALESCE(remove_72h, FALSE)
        )::bigint,
        COUNT(*) FILTER (
            WHERE NOT COALESCE(purchase_72h, FALSE) AND COALESCE(remove_72h, FALSE)
        )::bigint
    FROM followup
)
SELECT
    *,
    ROUND(100.0 * purchase_count / NULLIF(common_cohort_count, 0), 4) AS purchase_rate_pct,
    ROUND(100.0 * unresolved_count / NULLIF(common_cohort_count, 0), 4) AS unresolved_rate_pct,
    ROUND(100.0 * remove_count / NULLIF(common_cohort_count, 0), 4) AS remove_rate_pct,
    ROUND(100.0 * purchase_count / NULLIF(purchase_count + remove_count, 0), 4) AS clear_purchase_rate_pct,
    ROUND(remove_count::numeric / NULLIF(purchase_count, 0), 4) AS remove_to_purchase_ratio
FROM window_counts
ORDER BY window_hours;
