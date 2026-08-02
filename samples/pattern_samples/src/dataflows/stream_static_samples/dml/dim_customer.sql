SELECT
    drv.CUSTOMER_ID,
    c.FIRST_NAME,
    c.LAST_NAME,
    c.EMAIL,
    ca.CITY,
    ca.STATE,
    c.DELETE_FLAG,
    drv.__START_AT
FROM
    STREAM(live.v_stream_static_dim_customer_sql_final_cdf_feed) AS drv
    JOIN {silver_schema}.base_customer_scd2 AS c ON drv.CUSTOMER_ID = c.CUSTOMER_ID
    JOIN {silver_schema}.base_customer_address_scd2 AS ca ON drv.CUSTOMER_ID = ca.CUSTOMER_ID