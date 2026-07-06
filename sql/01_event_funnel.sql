-- Event funnel examples.
-- These queries are read-only and use the raw table.

-- 1. Simple event-count funnel.
SELECT
    event_type,
    COUNT(*) AS event_count
FROM makeup_consumer_events.dec
WHERE event_type IN ('view', 'cart', 'remove_from_cart', 'purchase')
GROUP BY event_type
ORDER BY
    CASE event_type
        WHEN 'view' THEN 1
        WHEN 'cart' THEN 2
        WHEN 'remove_from_cart' THEN 3
        WHEN 'purchase' THEN 4
        ELSE 99
    END;

-- 2. User-product path funnel.
-- Grain: one user_id + product_id path in December.
WITH user_product_events AS (
    SELECT
        user_id,
        product_id,
        STRING_AGG(event_type, ',' ORDER BY event_time::timestamptz) AS event_sequence
    FROM makeup_consumer_events.dec
    GROUP BY user_id, product_id
)
SELECT
    COUNT(*) FILTER (WHERE event_sequence ILIKE '%view%') AS total_with_view,
    COUNT(*) FILTER (WHERE event_sequence ILIKE '%view%' AND event_sequence ILIKE '%cart%') AS total_with_cart,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE event_sequence ILIKE '%view%' AND event_sequence ILIKE '%cart%')
        / NULLIF(COUNT(*) FILTER (WHERE event_sequence ILIKE '%view%'), 0),
        2
    ) AS view_to_cart_rate_pct,
    COUNT(*) FILTER (WHERE event_sequence ILIKE '%cart%purchase%') AS cart_to_purchase_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE event_sequence ILIKE '%cart%purchase%')
        / NULLIF(COUNT(*) FILTER (WHERE event_sequence ILIKE '%cart%'), 0),
        2
    ) AS cart_to_purchase_rate_pct
FROM user_product_events;

