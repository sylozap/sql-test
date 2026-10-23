SELECT c.client_id, c.full_name
FROM clients c
WHERE NOT EXISTS (
    SELECT 1 FROM accounts a WHERE a.client_id = c.client_id
)
ORDER BY c.client_id;
