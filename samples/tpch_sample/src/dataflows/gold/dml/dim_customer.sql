SELECT
    xxhash64('customer', drv.customer_key, drv.__START_AT) AS customer_sk,
    drv.customer_key                           AS customer_key,
    c.customer_name                            AS customer_name,
    ca.address                                 AS address,
    cp.phone                                   AS phone,
    ca.nation_key                              AS nation_key,
    n.nation_name                              AS nation_name,
    r.region_name                              AS region_name,
    c.market_segment                           AS market_segment,
    c.account_balance                          AS account_balance,
    drv.__START_AT                             AS __START_AT
FROM
    STREAM(live.v_stg_customer_dedupe_cdf_feed) AS drv
    JOIN {silver_schema}.customer AS c
        ON drv.customer_key = c.customer_key
        AND drv.__START_AT >= c.__START_AT
        AND (drv.__START_AT < c.__END_AT OR c.__END_AT IS NULL)
    JOIN {silver_schema}.customer_address AS ca
        ON drv.customer_key = ca.customer_key
        AND drv.__START_AT >= ca.__START_AT
        AND (drv.__START_AT < ca.__END_AT OR ca.__END_AT IS NULL)
    JOIN {silver_schema}.customer_phone AS cp
        ON drv.customer_key = cp.customer_key
        AND drv.__START_AT >= cp.__START_AT
        AND (drv.__START_AT < cp.__END_AT OR cp.__END_AT IS NULL)
    LEFT JOIN {silver_schema}.nation AS n ON ca.nation_key = n.nation_key
    LEFT JOIN {silver_schema}.region AS r ON n.region_key = r.region_key
