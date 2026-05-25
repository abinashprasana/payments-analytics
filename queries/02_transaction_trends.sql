-- Trace processing volume and total revenue growth trends over monthly periods
SELECT
    DATE_TRUNC('month', transaction_date) AS transaction_month,
    COUNT(transaction_id) AS transaction_volume,
    SUM(amount) AS total_value,
    ROUND(AVG(amount), 2) AS average_value
FROM
    transactions
WHERE
    status = 'completed'
GROUP BY
    transaction_month
ORDER BY
    transaction_month ASC;
