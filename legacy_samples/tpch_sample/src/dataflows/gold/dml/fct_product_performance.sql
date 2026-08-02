SELECT
    date_format(f.order_date, 'yyyy-MM')                            AS sales_month,
    p.brand                                                        AS brand,
    p.part_type                                                    AS part_type,
    sum(f.quantity)                                                AS units_sold,
    sum(f.extended_price)                                          AS gross_sales,
    sum(f.net_sales)                                               AS net_sales,
    sum(f.net_sales) / nullif(sum(f.quantity), 0)                  AS avg_selling_price,
    sum(CASE WHEN f.return_flag = 'R' THEN f.quantity ELSE 0 END) / nullif(sum(f.quantity), 0) AS return_rate
FROM
    live.fct_order_lines AS f
    JOIN live.dim_part AS p ON f.part_key = p.part_key AND p.__END_AT IS NULL
GROUP BY
    date_format(f.order_date, 'yyyy-MM'),
    p.brand,
    p.part_type
