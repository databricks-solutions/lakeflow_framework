SELECT
    date_format(f.order_date, 'yyyy-MM')                                 AS sales_month,
    s.supplier_key                                                      AS supplier_key,
    s.supplier_name                                                     AS supplier_name,
    sum(f.net_sales)                                                    AS net_sales_supplied,
    sum(f.quantity)                                                     AS units_supplied,
    avg(CASE WHEN f.receipt_date <= f.commit_date THEN 1.0 ELSE 0.0 END) AS on_time_rate,
    sum(CASE WHEN f.return_flag = 'R' THEN f.quantity ELSE 0 END) / nullif(sum(f.quantity), 0) AS return_rate,
    sum(f.net_sales) - sum(f.quantity * ps.supply_cost)                AS est_gross_margin,
    (sum(f.net_sales) - sum(f.quantity * ps.supply_cost)) / nullif(sum(f.net_sales), 0) AS est_margin_pct
FROM
    live.fct_order_lines AS f
    JOIN live.dim_supplier AS s     ON f.supplier_key = s.supplier_key AND s.__END_AT IS NULL
    JOIN live.fct_part_supply AS ps ON f.part_key = ps.part_key AND f.supplier_key = ps.supplier_key
GROUP BY
    date_format(f.order_date, 'yyyy-MM'),
    s.supplier_key,
    s.supplier_name
