-- Brand quadrant matrix in SQL.
--
-- This file produces the brand-level A/C metrics used by the quadrant analysis.
-- It does not draw the chart; it creates the table behind the chart.
--
-- Default source below uses the original full-month grouped table.
-- For 48-hour口径, replace "03_user_behavior_groups" with
-- "11_user_behavior_groups_window_48h".

WITH cleaned AS (
    SELECT
        CASE
            WHEN brand IS NULL OR BTRIM(brand::text) = '' THEN 'Unknown Brand'
            WHEN LOWER(BTRIM(brand::text)) IN ('nan', 'null', 'none') THEN 'Unknown Brand'
            ELSE BTRIM(brand::text)
        END AS brand_clean,
        group_type
    FROM makeup_consumer_events."03_user_behavior_groups"
    WHERE group_type IN ('A', 'C')
),
brand_stats AS (
    SELECT
        brand_clean,
        COUNT(*) FILTER (WHERE group_type = 'A') AS a_count,
        COUNT(*) FILTER (WHERE group_type = 'C') AS c_count
    FROM cleaned
    GROUP BY brand_clean
),
metrics AS (
    SELECT
        brand_clean,
        a_count,
        c_count,
        a_count + c_count AS clear_outcome_count,
        a_count::numeric / NULLIF(a_count + c_count, 0) AS ac_purchase_share,
        c_count::numeric / NULLIF(a_count + c_count, 0) AS ac_loss_share,
        c_count::numeric / NULLIF(a_count, 0) AS c_to_a_ratio,
        (a_count + c_count)::numeric / SUM(a_count + c_count) OVER () AS brand_share_in_clear_outcome
    FROM brand_stats
),
qualified AS (
    SELECT *
    FROM metrics
    WHERE brand_clean <> 'Unknown Brand'
      AND clear_outcome_count >= 100
      AND a_count > 0
),
thresholds AS (
    SELECT
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY brand_share_in_clear_outcome) AS share_threshold,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY c_to_a_ratio) AS median_risk_threshold,
        1.5::numeric AS fixed_risk_threshold
    FROM qualified
)
SELECT
    q.brand_clean,
    q.a_count,
    q.c_count,
    q.clear_outcome_count,
    ROUND(q.ac_purchase_share, 4) AS ac_purchase_share,
    ROUND(q.ac_loss_share, 4) AS ac_loss_share,
    ROUND(q.c_to_a_ratio, 4) AS c_to_a_ratio,
    ROUND(q.brand_share_in_clear_outcome, 6) AS brand_share_in_clear_outcome,
    CASE
        WHEN q.brand_share_in_clear_outcome >= t.share_threshold
         AND q.c_to_a_ratio >= t.median_risk_threshold THEN 'priority_fix'
        WHEN q.brand_share_in_clear_outcome >= t.share_threshold
         AND q.c_to_a_ratio < t.median_risk_threshold THEN 'core_healthy'
        WHEN q.brand_share_in_clear_outcome < t.share_threshold
         AND q.c_to_a_ratio >= t.median_risk_threshold THEN 'problem_long_tail'
        ELSE 'potential_long_tail'
    END AS median_threshold_quadrant,
    CASE
        WHEN q.brand_share_in_clear_outcome >= t.share_threshold
         AND q.c_to_a_ratio >= t.fixed_risk_threshold THEN 'priority_fix'
        WHEN q.brand_share_in_clear_outcome >= t.share_threshold
         AND q.c_to_a_ratio < t.fixed_risk_threshold THEN 'core_healthy'
        WHEN q.brand_share_in_clear_outcome < t.share_threshold
         AND q.c_to_a_ratio >= t.fixed_risk_threshold THEN 'problem_long_tail'
        ELSE 'potential_long_tail'
    END AS fixed_risk_1_5_quadrant,
    ROUND(t.share_threshold, 6) AS share_threshold,
    ROUND(t.median_risk_threshold, 6) AS median_risk_threshold,
    t.fixed_risk_threshold
FROM qualified q
CROSS JOIN thresholds t
ORDER BY clear_outcome_count DESC;

