-- Basic table checks for the raw December event table.
-- Run this first to understand the table shape before writing analysis SQL.

-- 1. Preview rows.
SELECT
    event_time,
    event_type,
    product_id,
    category_id,
    category_code,
    brand,
    price,
    user_id,
    user_session
FROM makeup_consumer_events.dec
LIMIT 20;

-- 2. Row count and event time range.
SELECT
    COUNT(*) AS total_rows,
    MIN(event_time::timestamptz) AS min_event_time,
    MAX(event_time::timestamptz) AS max_event_time
FROM makeup_consumer_events.dec;

-- 3. Event type distribution.
SELECT
    event_type,
    COUNT(*) AS event_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS event_share_pct
FROM makeup_consumer_events.dec
GROUP BY event_type
ORDER BY event_count DESC;

-- 4. Basic distinct counts.
SELECT
    COUNT(DISTINCT user_id) AS distinct_users,
    COUNT(DISTINCT user_session) AS distinct_sessions,
    COUNT(DISTINCT product_id) AS distinct_products,
    COUNT(DISTINCT brand) AS distinct_brands
FROM makeup_consumer_events.dec;

