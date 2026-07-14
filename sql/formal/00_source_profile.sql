SET TIME ZONE 'UTC';

WITH source_summary AS MATERIALIZED (
    SELECT
        COUNT(*)::bigint AS source_row_count,
        MIN(event_time::timestamptz) AS source_min_time_utc,
        MAX(event_time::timestamptz) AS source_max_time_utc,
        COUNT(DISTINCT event_time::date)::bigint AS covered_utc_dates,
        COUNT(DISTINCT user_id)::bigint AS distinct_users,
        COUNT(DISTINCT user_session)::bigint AS distinct_sessions,
        COUNT(DISTINCT product_id)::bigint AS distinct_products,
        COUNT(DISTINCT CASE
            WHEN brand IS NOT NULL
             AND BTRIM(brand) <> ''
             AND LOWER(BTRIM(brand)) NOT IN ('nan', 'null', 'none')
            THEN BTRIM(brand)
        END)::bigint AS distinct_known_brands,
        COUNT(*) FILTER (WHERE user_id IS NULL)::bigint AS missing_user_id_rows,
        COUNT(*) FILTER (
            WHERE user_session IS NULL
               OR BTRIM(user_session) = ''
               OR LOWER(BTRIM(user_session)) IN ('nan', 'null', 'none')
        )::bigint AS missing_session_rows,
        COUNT(*) FILTER (WHERE product_id IS NULL)::bigint AS missing_product_id_rows,
        COUNT(*) FILTER (
            WHERE brand IS NULL OR BTRIM(brand) = '' OR LOWER(BTRIM(brand)) IN ('nan', 'null', 'none')
        )::bigint AS missing_brand_rows,
        COUNT(*) FILTER (
            WHERE category_code IS NULL
               OR BTRIM(category_code) = ''
               OR LOWER(BTRIM(category_code)) IN ('nan', 'null', 'none')
        )::bigint AS missing_category_code_rows,
        COUNT(*) FILTER (WHERE category_id IS NULL)::bigint AS missing_category_id_rows,
        COUNT(*) FILTER (WHERE price IS NULL)::bigint AS missing_price_rows,
        COUNT(*) FILTER (WHERE price <= 0)::bigint AS nonpositive_price_rows,
        COUNT(*) FILTER (
            WHERE event_type IS NULL
               OR event_type NOT IN ('view', 'cart', 'remove_from_cart', 'purchase')
        )::bigint AS unexpected_event_type_rows
    FROM makeup_consumer_events.dec
),
exact_duplicate_summary AS (
    SELECT COALESCE(SUM(duplicate_count - 1), 0)::bigint AS exact_duplicate_excess_rows
    FROM (
        SELECT COUNT(*)::bigint AS duplicate_count
        FROM makeup_consumer_events.dec
        GROUP BY
            event_time,
            event_type,
            product_id,
            category_id,
            category_code,
            brand,
            price,
            user_id,
            user_session
        HAVING COUNT(*) > 1
    ) d
)
SELECT s.*, d.exact_duplicate_excess_rows
FROM source_summary s
CROSS JOIN exact_duplicate_summary d;
