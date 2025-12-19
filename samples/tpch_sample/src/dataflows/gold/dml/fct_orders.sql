SELECT
    o.o_orderkey as order_key,
    l.l_linenumber as line_number,
    c.c_custkey as customer_key,
    l.l_partkey as part_key,
    l.l_suppkey as supplier_key,
    o.o_orderdate as order_date,
    o.o_orderstatus as order_status,
    l.l_quantity as quantity,
    l.l_extendedprice as extended_price,
    l.l_discount as discount,
    l.l_tax as tax,
    l.l_returnflag as return_flag,
    l.l_linestatus as line_status,
    l.l_shipdate as ship_date,
    l.l_commitdate as commit_date,
    l.l_receiptdate as receipt_date,
    l.l_shipinstruct as ship_instruct,
    l.l_shipmode as ship_mode,
    l.l_comment as comment,
    l.__START_AT
FROM
    STREAM(live.v_lineitem_cdf_feed) AS l
    JOIN {silver_schema}.orders AS o ON l.l_orderkey = o.o_orderkey
    JOIN {silver_schema}.customer AS c ON o.o_custkey = c.c_custkey
