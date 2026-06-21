SELECT *
FROM (
  SELECT customer_id, product, quantity
  FROM micro_batch_view
) src
PIVOT (
  SUM(quantity)
  FOR product IN ('apples', 'bananas', 'oranges', 'pears')
)