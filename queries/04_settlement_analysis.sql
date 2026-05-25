-- Audit payout processing latency across merchant categories to monitor SLA targets
SELECT
    m.category AS merchant_category,
    COUNT(s.settlement_id) AS settlement_count,
    ROUND(
        AVG(EXTRACT(EPOCH FROM (s.settlement_date - t.transaction_date)) / 86400)::NUMERIC,
        2
    ) AS avg_settlement_days
FROM
    settlements s
INNER JOIN
    transactions t ON s.transaction_id = t.transaction_id
INNER JOIN
    merchants m ON t.merchant_id = m.merchant_id
GROUP BY
    m.category
ORDER BY
    avg_settlement_days ASC;
