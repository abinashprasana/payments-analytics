-- Track monthly customer retention cohorts over time based on completed transactions
WITH customer_cohorts AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', join_date) AS cohort_month
    FROM
        customers
),
monthly_active_customers AS (
    SELECT DISTINCT
        c.customer_id,
        cc.cohort_month,
        DATE_TRUNC('month', t.transaction_date) AS activity_month
    FROM
        transactions t
    INNER JOIN
        accounts a ON t.account_id = a.account_id
    INNER JOIN
        customers c ON a.customer_id = c.customer_id
    INNER JOIN
        customer_cohorts cc ON c.customer_id = cc.customer_id
    WHERE
        t.status = 'completed'
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(customer_id) AS cohort_size
    FROM
        customer_cohorts
    GROUP BY
        cohort_month
),
cohort_retention AS (
    SELECT
        ma.cohort_month,
        -- Calculate the month offset since joining the platform
        (EXTRACT(YEAR FROM AGE(ma.activity_month, ma.cohort_month)) * 12 +
         EXTRACT(MONTH FROM AGE(ma.activity_month, ma.cohort_month)))::INTEGER AS months_active_offset,
        COUNT(DISTINCT ma.customer_id) AS active_customers
    FROM
        monthly_active_customers ma
    GROUP BY
        ma.cohort_month,
        months_active_offset
)
SELECT
    cr.cohort_month,
    sz.cohort_size,
    cr.months_active_offset,
    cr.active_customers,
    ROUND(cr.active_customers::NUMERIC / sz.cohort_size, 4) AS retention_rate,
    -- Compute the step-change in active customer count compared to the previous month
    LAG(cr.active_customers) OVER (
        PARTITION BY cr.cohort_month
        ORDER BY cr.months_active_offset
    ) AS prev_month_active_customers
FROM
    cohort_retention cr
INNER JOIN
    cohort_sizes sz ON cr.cohort_month = sz.cohort_month
ORDER BY
    cr.cohort_month ASC,
    cr.months_active_offset ASC;
