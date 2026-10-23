SELECT account_id, tx_date, amount,
       COUNT(*) AS cnt,
       ARRAY_AGG(tx_id ORDER BY tx_id) AS tx_ids
FROM transactions
GROUP BY account_id, tx_date, amount
HAVING COUNT(*) > 1
ORDER BY account_id, tx_date;

-- лишние копии (если нужно удалить дубли, оставив по одной):
-- SELECT *
-- FROM (SELECT t.*,
--              ROW_NUMBER() OVER (PARTITION BY account_id, tx_date, amount ORDER BY tx_id) AS rn
--       FROM transactions t) d
-- WHERE rn > 1;
