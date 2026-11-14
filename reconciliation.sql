-- 1. Current row count must be exactly one per customer in the dimension.
SELECT customer_id, COUNT(*) AS current_rows
FROM customer_dimension
WHERE is_current = 1
GROUP BY customer_id
HAVING COUNT(*) <> 1;

-- 2. No overlapping or reversed validity intervals (exclusive end boundary).
SELECT a.customer_id, a.customer_sk, b.customer_sk
FROM customer_dimension a
JOIN customer_dimension b
  ON a.customer_id = b.customer_id
 AND a.customer_sk < b.customer_sk
 AND (a.effective_to IS NULL OR b.effective_from < a.effective_to)
 AND (b.effective_to IS NULL OR a.effective_from < b.effective_to);

-- 3. Exactly one current row per customer (expected result: zero rows).
SELECT customer_id
FROM customer_dimension
GROUP BY customer_id
HAVING SUM(is_current) <> 1;

-- 4. Inspect history for a customer.
SELECT *
FROM customer_dimension
WHERE customer_id = 'C000001'
ORDER BY effective_from;

-- 5. Operational run history.
SELECT run_id, status, input_count, accepted_count, duplicate_count,
       rejected_count, output_count, started_at, ended_at, error_message
FROM pipeline_runs
ORDER BY started_at DESC;
