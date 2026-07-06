-- Focused checks for runail vs masura.
-- These queries support the "time x brand" and "price band x brand" analysis.

-- 1. Brand x hour x group distribution.
WITH target AS (
    SELECT
        LOWER(brand) AS brand,
        EXTRACT(HOUR FROM event_time::timestamptz) AS event_hour,
        group_type
    FROM makeup_consumer_events."03_user_behavior_groups"
    WHERE LOWER(brand) IN ('runail', 'masura')
),
counts AS (
    SELECT
        brand,
        event_hour,
        COUNT(*) FILTER (WHERE group_type = 'A') AS a_count,
        COUNT(*) FILTER (WHERE group_type = 'B') AS b_count,
        COUNT(*) FILTER (WHERE group_type = 'C') AS c_count,
        COUNT(*) AS total_count
    FROM target
    GROUP BY brand, event_hour
)
SELECT
    brand,
    event_hour,
    ROUND(100.0 * a_count / NULLIF(total_count, 0), 2) AS a_pct,
    ROUND(100.0 * b_count / NULLIF(total_count, 0), 2) AS b_pct,
    ROUND(100.0 * c_count / NULLIF(total_count, 0), 2) AS c_pct,
    ROUND((c_count::numeric / NULLIF(a_count, 0)), 2) AS c_to_a_ratio
FROM counts
ORDER BY brand, event_hour;

-- 2. Morning vs evening summary.
WITH target AS (
    SELECT
        LOWER(brand) AS brand,
        CASE
            WHEN EXTRACT(HOUR FROM event_time::timestamptz) BETWEEN 8 AND 11 THEN 'morning_8_11'
            WHEN EXTRACT(HOUR FROM event_time::timestamptz) BETWEEN 18 AND 21 THEN 'evening_18_21'
            ELSE 'other'
        END AS time_period,
        group_type
    FROM makeup_consumer_events."03_user_behavior_groups"
    WHERE LOWER(brand) IN ('runail', 'masura')
),
counts AS (
    SELECT
        brand,
        time_period,
        COUNT(*) FILTER (WHERE group_type = 'A') AS a_count,
        COUNT(*) FILTER (WHERE group_type = 'B') AS b_count,
        COUNT(*) FILTER (WHERE group_type = 'C') AS c_count,
        COUNT(*) AS total_count
    FROM target
    WHERE time_period <> 'other'
    GROUP BY brand, time_period
)
SELECT
    brand,
    time_period,
    ROUND(100.0 * a_count / total_count, 2) AS a_pct,
    ROUND(100.0 * b_count / total_count, 2) AS b_pct,
    ROUND(100.0 * c_count / total_count, 2) AS c_pct,
    ROUND(c_count::numeric / NULLIF(a_count, 0), 2) AS c_to_a_ratio
FROM counts
ORDER BY brand, time_period;

-- 3. Price band comparison for runail vs masura.
WITH target AS (
    SELECT
        LOWER(brand) AS brand,
        price,
        group_type,
        CASE
            WHEN price >= 0 AND price < 3 THEN '0-3'
            WHEN price >= 3 AND price < 6 THEN '3-6'
            WHEN price >= 6 AND price < 10 THEN '6-10'
            WHEN price >= 10 AND price < 15 THEN '10-15'
            WHEN price >= 15 AND price < 20 THEN '15-20'
            WHEN price >= 20 THEN '20+'
            ELSE 'unknown'
        END AS price_range
    FROM makeup_consumer_events."03_user_behavior_groups"
    WHERE LOWER(brand) IN ('runail', 'masura')
),
counts AS (
    SELECT
        price_range,
        brand,
        COUNT(*) FILTER (WHERE group_type = 'A') AS a_count,
        COUNT(*) FILTER (WHERE group_type = 'B') AS b_count,
        COUNT(*) FILTER (WHERE group_type = 'C') AS c_count,
        COUNT(*) AS total_count
    FROM target
    GROUP BY price_range, brand
)
SELECT
    price_range,
    brand,
    ROUND(100.0 * a_count / NULLIF(total_count, 0), 2) AS a_pct,
    ROUND(100.0 * b_count / NULLIF(total_count, 0), 2) AS b_pct,
    ROUND(100.0 * c_count / NULLIF(total_count, 0), 2) AS c_pct,
    total_count,
    ROUND(b_count::numeric / NULLIF(a_count, 0), 3) AS b_to_a_ratio,
    ROUND(c_count::numeric / NULLIF(a_count, 0), 3) AS c_to_a_ratio
FROM counts
ORDER BY
    CASE price_range
        WHEN '0-3' THEN 1
        WHEN '3-6' THEN 2
        WHEN '6-10' THEN 3
        WHEN '10-15' THEN 4
        WHEN '15-20' THEN 5
        WHEN '20+' THEN 6
        ELSE 99
    END,
    brand;

