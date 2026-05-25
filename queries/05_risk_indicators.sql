-- Identify merchants whose fraud rates exceed their category benchmark for risk mitigation
WITH merchant_metrics AS (
    SELECT
        t.merchant_id,
        m.merchant_name,
        m.category,
        COUNT(t.transaction_id) AS total_transactions,
        COUNT(f.flag_id) AS flagged_transactions,
        COUNT(f.flag_id)::NUMERIC / COUNT(t.transaction_id) AS merchant_fraud_rate
    FROM
        transactions t
    INNER JOIN
        merchants m ON t.merchant_id = m.merchant_id
    LEFT JOIN
        fraud_flags f ON t.transaction_id = f.transaction_id
    GROUP BY
        t.merchant_id,
        m.merchant_name,
        m.category
),
category_metrics AS (
    SELECT
        category,
        SUM(flagged_transactions)::NUMERIC / SUM(total_transactions) AS category_avg_fraud_rate
    FROM
        merchant_metrics
    GROUP BY
        category
)
SELECT
    mm.merchant_id,
    mm.merchant_name,
    mm.category,
    mm.total_transactions,
    mm.flagged_transactions,
    ROUND(mm.merchant_fraud_rate, 4) AS merchant_fraud_rate,
    ROUND(cm.category_avg_fraud_rate, 4) AS category_avg_fraud_rate
FROM
    merchant_metrics mm
INNER JOIN
    category_metrics cm ON mm.category = cm.category
WHERE
    mm.merchant_fraud_rate > cm.category_avg_fraud_rate
    AND mm.total_transactions >= 20
ORDER BY
    merchant_fraud_rate DESC,
    mm.total_transactions DESC;
