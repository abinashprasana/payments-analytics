-- Calculate customer lifetime value metrics by chaining spending aggregates, active lifespan, and profile joins
WITH customer_spending AS (
    SELECT
        a.customer_id,
        SUM(t.amount) AS total_spend,
        ROUND(AVG(t.amount), 2) AS avg_transaction_value,
        COUNT(t.transaction_id) AS completed_transaction_count
    FROM
        transactions t
    INNER JOIN
        accounts a ON t.account_id = a.account_id
    WHERE
        t.status = 'completed'
    GROUP BY
        a.customer_id
),
customer_lifespan AS (
    SELECT
        a.customer_id,
        MIN(t.transaction_date) AS first_transaction,
        MAX(t.transaction_date) AS last_transaction,
        GREATEST(
            1,
            EXTRACT(YEAR FROM AGE(MAX(t.transaction_date), MIN(t.transaction_date))) * 12 +
            EXTRACT(MONTH FROM AGE(MAX(t.transaction_date), MIN(t.transaction_date)))
        )::INTEGER AS months_active
    FROM
        transactions t
    INNER JOIN
        accounts a ON t.account_id = a.account_id
    WHERE
        t.status = 'completed'
    GROUP BY
        a.customer_id
)
SELECT
    c.customer_id,
    c.full_name,
    c.segment,
    c.country,
    cs.completed_transaction_count,
    cs.total_spend AS customer_lifetime_value,
    cs.avg_transaction_value,
    cl.months_active,
    -- Compute average customer spending volume per active month
    ROUND(cs.total_spend / cl.months_active, 2) AS revenue_per_month
FROM
    customers c
INNER JOIN
    customer_spending cs ON c.customer_id = cs.customer_id
INNER JOIN
    customer_lifespan cl ON c.customer_id = cl.customer_id
ORDER BY
    customer_lifetime_value DESC
LIMIT 50;
