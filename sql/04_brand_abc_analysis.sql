-- Brand distribution across A/B/C groups.
-- This query reproduces the core brand-share idea from the notebook.

WITH cleaned AS (
    SELECT
        CASE
            WHEN brand IS NULL OR BTRIM(brand::text) = '' THEN 'Unknown Brand'
            WHEN LOWER(BTRIM(brand::text)) IN ('nan', 'null', 'none') THEN 'Unknown Brand'
            ELSE BTRIM(brand::text)
        END AS brand_clean,
        group_type
    FROM makeup_consumer_events."03_user_behavior_groups"
),
brand_group_counts AS (
    SELECT
        brand_clean,
        group_type,
        COUNT(*) AS row_count
    FROM cleaned
    GROUP BY brand_clean, group_type
),
group_totals AS (
    SELECT
        group_type,
        SUM(row_count) AS group_total
    FROM brand_group_counts
    GROUP BY group_type
)
SELECT
    bgc.brand_clean,
    bgc.group_type,
    bgc.row_count,
    ROUND(100.0 * bgc.row_count / gt.group_total, 2) AS brand_share_in_group_pct
FROM brand_group_counts bgc
JOIN group_totals gt
    ON gt.group_type = bgc.group_type
ORDER BY bgc.group_type, brand_share_in_group_pct DESC;

-- Wide table for top brands: A/B/C share side by side.
WITH cleaned AS (
    SELECT
        CASE
            WHEN brand IS NULL OR BTRIM(brand::text) = '' THEN 'Unknown Brand'
            WHEN LOWER(BTRIM(brand::text)) IN ('nan', 'null', 'none') THEN 'Unknown Brand'
            ELSE BTRIM(brand::text)
        END AS brand_clean,
        group_type
    FROM makeup_consumer_events."03_user_behavior_groups"
),
counts AS (
    SELECT brand_clean, group_type, COUNT(*) AS row_count
    FROM cleaned
    GROUP BY brand_clean, group_type
),
shares AS (
    SELECT
        brand_clean,
        group_type,
        100.0 * row_count / SUM(row_count) OVER (PARTITION BY group_type) AS share_pct
    FROM counts
)
SELECT
    brand_clean,
    ROUND(MAX(share_pct) FILTER (WHERE group_type = 'A')::numeric, 2) AS a_share_pct,
    ROUND(MAX(share_pct) FILTER (WHERE group_type = 'B')::numeric, 2) AS b_share_pct,
    ROUND(MAX(share_pct) FILTER (WHERE group_type = 'C')::numeric, 2) AS c_share_pct,
    ROUND(
        (
            COALESCE(MAX(share_pct) FILTER (WHERE group_type = 'A'), 0)
            - COALESCE(MAX(share_pct) FILTER (WHERE group_type = 'C'), 0)
        )::numeric,
        2
    ) AS a_minus_c_pp
FROM shares
GROUP BY brand_clean
ORDER BY c_share_pct DESC NULLS LAST
LIMIT 50;

