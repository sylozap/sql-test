-- диапазон, а не EXTRACT(YEAR ...): так может использоваться индекс по registered_at
SELECT client_id, full_name, city, registered_at
FROM clients
WHERE city = 'Новосибирск'
  AND registered_at >= DATE '2025-01-01'
  AND registered_at <  DATE '2026-01-01'
ORDER BY registered_at;
