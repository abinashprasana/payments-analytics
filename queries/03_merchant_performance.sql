-- Rank merchants by total settled revenue within their categories to identify top partners
WITH merchant_revenue AS (
    SELECT
        m.merchant_id,
        m.merchant_name,
        m.category,
        m.risk_tier,
        SUM(s.settled_amount) AS total_revenue
    FROM
        merchants m
    INNER JOIN
        transactions t ON m.merchant_id = t.merchant_id
    INNER JOIN
        settlements s ON t.transaction_id = s.transaction_id
    WHERE
        t.status = 'completed'
    GROUP BY
        m.merchant_id,
        m.merchant_name,
        m.category,
        m.risk_tier
)
SELECT
    merchant_id,
    merchant_name,
    category,
    risk_tier,
    total_revenue,
    RANK() OVER (
        PARTITION BY category
        ORDER BY total_revenue DESC
    ) AS category_revenue_rank
FROM
    merchant_revenue
ORDER BY
    total_revenue DESC
LIMIT 20;
