WITH monthly_out AS (
    SELECT date_trunc('month', t.tx_date)::date AS month,
           a.client_id,
           SUM(t.amount) AS total_out
    FROM transactions t
    JOIN accounts a ON a.account_id = t.account_id
    WHERE t.tx_type = 'out'
    GROUP BY 1, 2
),
ranked AS (
    SELECT m.*,
           ROW_NUMBER() OVER (PARTITION BY month ORDER BY total_out DESC, client_id) AS rn
    FROM monthly_out m
)
SELECT r.month, r.rn, r.client_id, c.full_name, r.total_out
FROM ranked r
JOIN clients c ON c.client_id = r.client_id
WHERE r.rn <= 3
ORDER BY r.month, r.rn;
