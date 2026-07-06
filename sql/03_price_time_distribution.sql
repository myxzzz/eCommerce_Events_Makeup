-- Price and time distribution checks by A/B/C group.
-- Default source: original grouped table.
-- To use the 48-hour table, replace "03_user_behavior_groups" with
-- "11_user_behavior_groups_window_48h".

-- 1. Price summary by group.
SELECT
    group_type,
    COUNT(*) AS row_count,
    ROUND(AVG(price)::numeric, 2) AS avg_price,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price)::numeric, 2) AS median_price,
    ROUND(STDDEV(price)::numeric, 2) AS std_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price
FROM makeup_consumer_events."03_user_behavior_groups"
GROUP BY group_type
ORDER BY group_type;

-- 2. Hour distribution by group.
SELECT
    group_type,
    EXTRACT(HOUR FROM event_time::timestamptz) AS event_hour,
    COUNT(*) AS row_count
FROM makeup_consumer_events."03_user_behavior_groups"
GROUP BY group_type, event_hour
ORDER BY group_type, event_hour;

-- 3. A/C only: hour distribution share inside each group.
WITH hourly AS (
    SELECT
        group_type,
        EXTRACT(HOUR FROM event_time::timestamptz) AS event_hour,
        COUNT(*) AS row_count
    FROM makeup_consumer_events."03_user_behavior_groups"
    WHERE group_type IN ('A', 'C')
    GROUP BY group_type, event_hour
)
SELECT
    group_type,
    event_hour,
    row_count,
    ROUND(100.0 * row_count / SUM(row_count) OVER (PARTITION BY group_type), 2) AS share_in_group_pct
FROM hourly
ORDER BY group_type, event_hour;

