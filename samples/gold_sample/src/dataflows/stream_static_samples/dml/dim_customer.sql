SELECT
    drv.CUSTOMER_ID,
    c.FIRST_NAME,
    c.LAST_NAME,
    c.EMAIL,
    ca.CITY,
    ca.STATE,
    c.DELETE_FLAG,
    drv.__START_AT AS SEQUENCE_BY_COLUMN
FROM
    STREAM(live.v_final_cdf_feed) AS drv
    LEFT JOIN {bronze_schema}.customer AS c ON drv.CUSTOMER_ID = c.CUSTOMER_ID
    LEFT JOIN {bronze_schema}.customer_address AS ca ON drv.CUSTOMER_ID = ca.CUSTOMER_ID