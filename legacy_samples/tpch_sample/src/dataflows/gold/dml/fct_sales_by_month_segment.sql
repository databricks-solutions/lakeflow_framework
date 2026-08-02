SELECT
    date_format(f.order_date, 'yyyy-MM')    AS sales_month,
    c.market_segment                        AS market_segment,
    loc.region_name                         AS region_name,
    count(DISTINCT f.order_key)             AS order_count,
    sum(f.quantity)                         AS total_quantity,
    sum(f.extended_price)                   AS gross_sales,
    sum(f.net_sales)                        AS net_sales,
    avg(f.discount)                         AS avg_discount
FROM
    live.fct_order_lines AS f
    JOIN live.dim_customer AS c   ON f.customer_key = c.customer_key AND c.__END_AT IS NULL
    JOIN live.dim_location AS loc ON c.nation_key = loc.nation_key
GROUP BY
    date_format(f.order_date, 'yyyy-MM'),
    c.market_segment,
    loc.region_name
