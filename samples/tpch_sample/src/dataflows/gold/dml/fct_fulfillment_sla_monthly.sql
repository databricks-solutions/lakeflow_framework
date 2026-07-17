SELECT
    date_format(f.order_date, 'yyyy-MM')                                 AS sales_month,
    s.nation_name                                                       AS supplier_nation,
    f.ship_mode                                                         AS ship_mode,
    count(*)                                                            AS line_count,
    avg(CASE WHEN f.receipt_date <= f.commit_date THEN 1.0 ELSE 0.0 END) AS on_time_rate,
    avg(CASE WHEN f.receipt_date > f.commit_date THEN 1.0 ELSE 0.0 END)  AS late_rate,
    avg(datediff(f.receipt_date, f.order_date))                         AS avg_lead_time_days,
    avg(datediff(f.receipt_date, f.ship_date))                          AS avg_transit_days
FROM
    live.fct_order_lines AS f
    JOIN live.dim_supplier AS s ON f.supplier_key = s.supplier_key AND s.__END_AT IS NULL
GROUP BY
    date_format(f.order_date, 'yyyy-MM'),
    s.nation_name,
    f.ship_mode
