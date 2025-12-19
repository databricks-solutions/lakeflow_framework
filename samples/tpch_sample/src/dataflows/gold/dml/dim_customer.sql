SELECT
    drv.c_custkey as customer_key,
    c.c_name as customer_name,
    ca.c_address as customer_address,
    cp.c_phone as customer_phone,
    ca.c_nationkey as nation_key,
    c.c_mktsegment as market_segment,
    drv.__START_AT as __START_AT
FROM
    STREAM(live.v_stg_customer_dedupe_cdf_feed) AS drv
    JOIN {silver_schema}.customer AS c ON drv.c_custkey = c.c_custkey
    JOIN {silver_schema}.customer_address AS ca ON drv.c_custkey = ca.c_custkey
    JOIN {silver_schema}.customer_phone AS cp ON drv.c_custkey = cp.c_custkey