SELECT
    xxhash64('supplier', s.supplier_key, s.__START_AT) AS supplier_sk,
    s.supplier_key      AS supplier_key,
    s.supplier_name     AS supplier_name,
    sa.address          AS supplier_address,
    sp.phone            AS supplier_phone,
    sa.nation_key       AS nation_key,
    n.nation_name       AS nation_name,
    r.region_name       AS region_name,
    s.account_balance   AS account_balance,
    s.__START_AT        AS __START_AT,
    s.__END_AT          AS __END_AT
FROM
    {silver_schema}.supplier AS s
    JOIN {silver_schema}.supplier_address AS sa ON s.supplier_key = sa.supplier_key AND sa.__END_AT IS NULL
    JOIN {silver_schema}.supplier_phone AS sp   ON s.supplier_key = sp.supplier_key AND sp.__END_AT IS NULL
    JOIN {silver_schema}.nation AS n            ON sa.nation_key = n.nation_key
    JOIN {silver_schema}.region AS r            ON n.region_key = r.region_key
UNION ALL
-- Unknown member: facts whose supplier has not arrived (or whose version was tombstoned by a
-- delete) resolve here via the COALESCE in fct_order_lines.
SELECT
    CAST(-1 AS BIGINT)          AS supplier_sk,
    CAST(-1 AS BIGINT)          AS supplier_key,
    'Unknown'                   AS supplier_name,
    'Unknown'                   AS supplier_address,
    'Unknown'                   AS supplier_phone,
    CAST(-1 AS BIGINT)          AS nation_key,
    'Unknown'                   AS nation_name,
    'Unknown'                   AS region_name,
    CAST(0 AS DECIMAL(18,2))    AS account_balance,
    CAST('1900-01-01' AS TIMESTAMP) AS __START_AT,
    CAST(NULL AS TIMESTAMP)     AS __END_AT
