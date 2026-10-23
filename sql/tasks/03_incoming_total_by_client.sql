SELECT c.client_id,
       c.full_name,
       COALESCE(SUM(t.amount), 0.00) AS total_in
FROM clients c
LEFT JOIN accounts a     ON a.client_id = c.client_id
LEFT JOIN transactions t ON t.account_id = a.account_id
                        AND t.tx_type = 'in'  
GROUP BY c.client_id, c.full_name
ORDER BY total_in DESC, c.client_id;
