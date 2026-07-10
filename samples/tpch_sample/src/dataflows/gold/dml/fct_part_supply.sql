SELECT
    ps.part_key         AS part_key,
    ps.supplier_key     AS supplier_key,
    dp.part_sk          AS part_sk,
    ds.supplier_sk      AS supplier_sk,
    ps.available_qty    AS available_qty,
    ps.supply_cost      AS supply_cost,
    dp.part_name        AS part_name,
    dp.manufacturer     AS manufacturer,
    ds.supplier_name    AS supplier_name
FROM
    {silver_schema}.partsupp AS ps
    JOIN live.dim_part AS dp     ON ps.part_key = dp.part_key AND dp.__END_AT IS NULL
    JOIN live.dim_supplier AS ds ON ps.supplier_key = ds.supplier_key AND ds.__END_AT IS NULL
