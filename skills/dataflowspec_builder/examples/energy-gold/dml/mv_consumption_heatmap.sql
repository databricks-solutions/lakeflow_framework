-- Hourly consumption heatmap by state and hour-of-day
-- Used as sqlPath source for a materialized view
SELECT
    c.state,
    HOUR(m.reading_timestamp) AS hour_of_day,
    DAYOFWEEK(m.reading_timestamp) AS day_of_week,
    CASE WHEN DAYOFWEEK(m.reading_timestamp) IN (1, 7) THEN 'weekend' ELSE 'weekday' END AS day_type,
    COUNT(*) AS reading_count,
    ROUND(AVG(m.kwh_used), 4) AS avg_kwh,
    ROUND(PERCENTILE_APPROX(m.kwh_used, 0.95), 4) AS p95_kwh,
    ROUND(STDDEV(m.kwh_used), 4) AS stddev_kwh
FROM {bronze_schema}.bronze_meter_readings m
INNER JOIN {silver_schema}.silver_customer_360 c
    ON m.customer_id = c.customer_id
WHERE m.kwh_used IS NOT NULL AND m.kwh_used >= 0
GROUP BY c.state, HOUR(m.reading_timestamp), DAYOFWEEK(m.reading_timestamp)
