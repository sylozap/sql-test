SELECT currency, COUNT(*) AS open_accounts
FROM accounts
WHERE closed_at IS NULL
GROUP BY currency
ORDER BY currency;
