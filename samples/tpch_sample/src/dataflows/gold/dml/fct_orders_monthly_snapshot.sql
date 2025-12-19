SELECT 
  CAST(date_trunc('month', o_orderdate) AS DATE) AS snapshot_month,
  o_custkey AS custkey,
  COUNT(DISTINCT o_orderkey) AS total_orders,
  CAST(SUM(l_quantity) AS DECIMAL(18,2)) AS total_quantity,
  CAST(SUM(l_extendedprice * (1 - l_discount)) AS DECIMAL(18,2)) AS total_sales,
  CAST(AVG(l_discount) AS DECIMAL(5,4)) AS avg_discount,
  CAST(MAX(l_extendedprice * (1 - l_discount)) AS DECIMAL(18,2)) AS max_order_total,
  CAST(MIN(l_extendedprice * (1 - l_discount)) AS DECIMAL(18,2)) AS min_order_total
FROM
    {silver_schema}.orders AS o 
    JOIN {silver_schema}.lineitem AS l ON o.o_orderkey = l.l_orderkey
GROUP BY 
  date_trunc('month', o_orderdate),
  o_custkey