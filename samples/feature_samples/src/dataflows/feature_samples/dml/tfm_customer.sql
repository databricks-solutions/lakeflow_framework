SELECT
  CUSTOMER_ID
  , FIRST_NAME
  , LAST_NAME
  , EMAIL
  , CITY
  , STATE
  , DELETE_FLAG
  , __START_AT
FROM stream(live.v_final_cdf_feed)