SET TIME ZONE 'UTC';

WITH raw AS MATERIALIZED (
    SELECT
        event_time::timestamptz AS event_time_utc,
        event_type,
        user_id,
        user_session,
        product_id
    FROM makeup_consumer_events.dec
    WHERE event_type IN ('view', 'cart', 'purchase')
),
event_level AS (
    SELECT
        event_type AS stage,
        COUNT(*)::bigint AS stage_count
    FROM raw
    GROUP BY event_type
),
user_level AS (
    SELECT
        event_type AS stage,
        COUNT(DISTINCT user_id)::bigint AS stage_count
    FROM raw
    GROUP BY event_type
),
session_level AS (
    SELECT
        event_type AS stage,
        COUNT(DISTINCT user_session)::bigint AS stage_count
    FROM raw
    WHERE user_session IS NOT NULL
      AND BTRIM(user_session) <> ''
      AND LOWER(BTRIM(user_session)) NOT IN ('nan', 'null', 'none')
    GROUP BY event_type
),
first_events AS MATERIALIZED (
    SELECT
        user_session,
        product_id,
        MIN(event_time_utc) FILTER (WHERE event_type = 'view') AS first_view_time,
        MIN(event_time_utc) FILTER (WHERE event_type = 'cart') AS first_cart_time,
        MIN(event_time_utc) FILTER (WHERE event_type = 'purchase') AS first_purchase_time
    FROM raw
    WHERE user_session IS NOT NULL
      AND BTRIM(user_session) <> ''
      AND LOWER(BTRIM(user_session)) NOT IN ('nan', 'null', 'none')
      AND product_id IS NOT NULL
    GROUP BY user_session, product_id
),
ordered_session_product AS (
    SELECT 'view'::text AS stage, COUNT(*) FILTER (WHERE first_view_time IS NOT NULL)::bigint AS stage_count
    FROM first_events
    UNION ALL
    SELECT 'cart', COUNT(*) FILTER (
        WHERE first_view_time IS NOT NULL
          AND first_cart_time > first_view_time
    )::bigint
    FROM first_events
    UNION ALL
    SELECT 'purchase', COUNT(*) FILTER (
        WHERE first_view_time IS NOT NULL
          AND first_cart_time > first_view_time
          AND first_purchase_time > first_cart_time
    )::bigint
    FROM first_events
),
combined AS (
    SELECT '事件级'::text AS metric_grain, stage, stage_count FROM event_level
    UNION ALL
    SELECT '用户级', stage, stage_count FROM user_level
    UNION ALL
    SELECT '会话级', stage, stage_count FROM session_level
    UNION ALL
    SELECT '会话-商品首事件顺序级', stage, stage_count FROM ordered_session_product
)
SELECT
    metric_grain,
    stage,
    CASE stage WHEN 'view' THEN 1 WHEN 'cart' THEN 2 WHEN 'purchase' THEN 3 END AS stage_order,
    stage_count,
    ROUND(
        100.0 * stage_count
        / NULLIF(MAX(stage_count) FILTER (WHERE stage = 'view') OVER (PARTITION BY metric_grain), 0),
        4
    ) AS vs_view_rate_pct,
    ROUND(
        100.0 * stage_count
        / NULLIF(LAG(stage_count) OVER (
            PARTITION BY metric_grain
            ORDER BY CASE stage WHEN 'view' THEN 1 WHEN 'cart' THEN 2 WHEN 'purchase' THEN 3 END
        ), 0),
        4
    ) AS vs_previous_stage_rate_pct
FROM combined
ORDER BY
    CASE metric_grain
        WHEN '事件级' THEN 1
        WHEN '用户级' THEN 2
        WHEN '会话级' THEN 3
        ELSE 4
    END,
    stage_order;
