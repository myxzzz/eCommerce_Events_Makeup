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
totals AS (
    SELECT COUNT(*)::numeric AS all_cohort_count
    FROM cohort
),
brand_counts AS (
    SELECT
        brand,
        COUNT(*)::bigint AS brand_cohort_count,
        COUNT(*) FILTER (WHERE group_type = 'A')::bigint AS purchase_count,
        COUNT(*) FILTER (WHERE group_type = 'B')::bigint AS unresolved_count,
        COUNT(*) FILTER (WHERE group_type = 'C')::bigint AS remove_count,
        COUNT(DISTINCT user_id)::bigint AS distinct_users,
        COUNT(DISTINCT user_session)::bigint AS distinct_sessions,
        COUNT(DISTINCT product_id)::bigint AS distinct_products
    FROM cohort
    WHERE brand IS NOT NULL
    GROUP BY brand
),
eligible AS (
    SELECT b.*, (b.purchase_count + b.remove_count)::bigint AS clear_outcome_count
    FROM brand_counts b
    WHERE b.purchase_count + b.remove_count >= 100
      AND b.purchase_count > 0
),
thresholds AS (
    SELECT
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY brand_cohort_count)::numeric AS volume_median_count,
        1.5::numeric AS remove_to_purchase_threshold
    FROM eligible
)
SELECT
    e.brand,
    e.brand_cohort_count,
    e.purchase_count,
    e.unresolved_count,
    e.remove_count,
    e.clear_outcome_count,
    e.distinct_users,
    e.distinct_sessions,
    e.distinct_products,
    ROUND(100.0 * e.brand_cohort_count / NULLIF(t.all_cohort_count, 0), 4) AS brand_share_pct,
    ROUND(100.0 * e.purchase_count / NULLIF(e.brand_cohort_count, 0), 4) AS purchase_rate_pct,
    ROUND(100.0 * e.unresolved_count / NULLIF(e.brand_cohort_count, 0), 4) AS unresolved_rate_pct,
    ROUND(100.0 * e.remove_count / NULLIF(e.brand_cohort_count, 0), 4) AS remove_rate_pct,
    ROUND(100.0 * e.purchase_count / NULLIF(e.clear_outcome_count, 0), 4) AS clear_purchase_rate_pct,
    ROUND(e.remove_count::numeric / NULLIF(e.purchase_count, 0), 4) AS remove_to_purchase_ratio,
    th.volume_median_count,
    th.remove_to_purchase_threshold,
    CASE WHEN e.brand_cohort_count >= th.volume_median_count THEN '高覆盖量' ELSE '低覆盖量' END AS volume_band,
    CASE
        WHEN e.remove_count::numeric / NULLIF(e.purchase_count, 0) >= th.remove_to_purchase_threshold
        THEN '高比值'
        ELSE '低比值'
    END AS risk_band,
    CASE
        WHEN e.brand_cohort_count >= th.volume_median_count
         AND e.remove_count::numeric / NULLIF(e.purchase_count, 0) >= th.remove_to_purchase_threshold
            THEN '优先核查'
        WHEN e.brand_cohort_count >= th.volume_median_count
            THEN '规模优势/维护'
        WHEN e.remove_count::numeric / NULLIF(e.purchase_count, 0) >= th.remove_to_purchase_threshold
            THEN '监控并补样本'
        ELSE '常规观察'
    END AS priority_quadrant
FROM eligible e
CROSS JOIN totals t
CROSS JOIN thresholds th
ORDER BY
    CASE
        WHEN e.brand_cohort_count >= th.volume_median_count
         AND e.remove_count::numeric / NULLIF(e.purchase_count, 0) >= th.remove_to_purchase_threshold
        THEN 0 ELSE 1
    END,
    e.brand_cohort_count DESC,
    remove_to_purchase_ratio DESC,
    e.brand;
