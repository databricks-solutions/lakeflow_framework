SELECT
    xxhash64('location', n.nation_key) AS location_sk,
    n.nation_key      AS nation_key,
    n.nation_name     AS nation_name,
    n.region_key      AS region_key,
    r.region_name     AS region_name
FROM
    {silver_schema}.nation AS n
    JOIN {silver_schema}.region AS r ON n.region_key = r.region_key
UNION ALL
-- Unknown member: facts referencing an unmapped nation resolve here.
SELECT
    CAST(-1 AS BIGINT) AS location_sk,
    CAST(-1 AS BIGINT) AS nation_key,
    'Unknown'          AS nation_name,
    CAST(-1 AS BIGINT) AS region_key,
    'Unknown'          AS region_name
