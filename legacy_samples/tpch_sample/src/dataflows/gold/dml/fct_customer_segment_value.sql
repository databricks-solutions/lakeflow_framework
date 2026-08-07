SELECT
    date_format(f.order_date, 'yyyy-MM')                                    AS sales_month,
    c.market_segment                                                       AS market_segment,
    loc.region_name                                                        AS region_name,
    count(DISTINCT f.customer_key)                                         AS active_customers,
    count(DISTINCT f.order_key)                                            AS order_count,
    sum(f.net_sales)                                                       AS net_sales,
    sum(f.net_sales) / nullif(count(DISTINCT f.order_key), 0)              AS avg_order_value,
    count(DISTINCT f.order_key) / nullif(count(DISTINCT f.customer_key), 0) AS orders_per_customer,
    sum(f.extended_price * f.discount) / nullif(sum(f.extended_price), 0)   AS weighted_discount_rate
FROM
    live.fct_order_lines AS f
    JOIN live.dim_customer AS c   ON f.customer_key = c.customer_key AND c.__END_AT IS NULL
    JOIN live.dim_location AS loc ON c.nation_key = loc.nation_key
GROUP BY
    date_format(f.order_date, 'yyyy-MM'),
    c.market_segment,
    loc.region_name
