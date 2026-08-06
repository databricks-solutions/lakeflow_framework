SELECT
    xxhash64('part', part_key, __START_AT) AS part_sk,
    part_key,
    part_name,
    manufacturer,
    brand,
    part_type,
    size,
    container,
    retail_price,
    comment,
    __START_AT,
    __END_AT
FROM
    {silver_schema}.part
UNION ALL
-- Unknown member: facts whose part has not arrived yet resolve here via the COALESCE in
-- fct_order_lines (late-arriving dimension handling).
SELECT
    CAST(-1 AS BIGINT)          AS part_sk,
    CAST(-1 AS BIGINT)          AS part_key,
    'Unknown'                   AS part_name,
    'Unknown'                   AS manufacturer,
    'Unknown'                   AS brand,
    'Unknown'                   AS part_type,
    CAST(-1 AS INT)             AS size,
    'Unknown'                   AS container,
    CAST(0 AS DECIMAL(18,2))    AS retail_price,
    'Unknown member'            AS comment,
    CAST('1900-01-01' AS TIMESTAMP) AS __START_AT,
    CAST(NULL AS TIMESTAMP)     AS __END_AT
