SELECT
    n.n_nationkey as nation_key,
    n.n_name as nation_name,
    r.r_name as region_name
FROM
    STREAM(live.v_nation_cdf_feed) AS n
    JOIN {silver_schema}.region AS r ON n.n_regionkey = r.r_regionkey