SELECT
    o.order_key                                              AS order_key,
    l.line_number                                            AS line_number,
    dc.customer_sk                                           AS customer_sk,
    COALESCE(ds.supplier_sk, -1)                             AS supplier_sk,
    COALESCE(dp.part_sk, -1)                                 AS part_sk,
    o.customer_key                                           AS customer_key,
    l.part_key                                               AS part_key,
    l.supplier_key                                           AS supplier_key,
    o.order_status                                           AS order_status,
    o.order_priority                                         AS order_priority,
    o.clerk                                                  AS clerk,
    o.ship_priority                                          AS ship_priority,
    o.order_date                                             AS order_date,
    l.ship_date                                              AS ship_date,
    l.commit_date                                            AS commit_date,
    l.receipt_date                                           AS receipt_date,
    CAST(date_format(o.order_date, 'yyyyMMdd') AS INT)       AS order_date_key,
    CAST(date_format(l.ship_date, 'yyyyMMdd') AS INT)        AS ship_date_key,
    CAST(date_format(l.commit_date, 'yyyyMMdd') AS INT)      AS commit_date_key,
    CAST(date_format(l.receipt_date, 'yyyyMMdd') AS INT)     AS receipt_date_key,
    l.quantity                                               AS quantity,
    l.extended_price                                         AS extended_price,
    l.discount                                               AS discount,
    l.tax                                                    AS tax,
    CAST(l.extended_price * (1 - l.discount) AS DECIMAL(18,2)) AS net_sales,
    l.return_flag                                            AS return_flag,
    l.line_status                                            AS line_status,
    l.ship_mode                                              AS ship_mode,
    l.ship_instruct                                          AS ship_instruct,
    l.comment                                                AS comment,
    l.load_timestamp                                         AS load_timestamp
FROM
    STREAM(live.v_lineitem_cdf_feed) AS l
    JOIN {silver_schema}.orders AS o ON l.order_key = o.order_key
    -- Point-in-time (as-of) resolution: pick the dimension version effective as of the order_date,
    -- so a fact row references the customer/supplier attributes as they were when the order was placed.
    LEFT JOIN live.dim_customer AS dc
        ON o.customer_key = dc.customer_key
        AND o.order_date >= dc.__START_AT
        AND (o.order_date < dc.__END_AT OR dc.__END_AT IS NULL)
    LEFT JOIN live.dim_supplier AS ds
        ON l.supplier_key = ds.supplier_key
        AND o.order_date >= ds.__START_AT
        AND (o.order_date < ds.__END_AT OR ds.__END_AT IS NULL)
    -- Part has no tracked changes -> resolve the current version.
    LEFT JOIN live.dim_part AS dp
        ON l.part_key = dp.part_key
        AND dp.__END_AT IS NULL
