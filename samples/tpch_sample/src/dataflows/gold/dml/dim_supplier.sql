SELECT
    drv.s_suppkey as supplier_key,
    s.s_name as supplier_name,
    sa.s_address as supplier_address,
    sp.s_phone as supplier_phone,
    n.n_nationkey as nation_key,
    drv.__START_AT
FROM
    STREAM(live.v_stg_supplier_dedupe_cdf_feed) AS drv
    JOIN {silver_schema}.supplier AS s ON drv.s_suppkey = s.s_suppkey
    JOIN {silver_schema}.supplier_address AS sa ON drv.s_suppkey = sa.s_suppkey
    JOIN {silver_schema}.supplier_phone AS sp ON drv.s_suppkey = sp.s_suppkey
    JOIN {silver_schema}.nation AS n ON sa.s_nationkey = n.n_nationkey