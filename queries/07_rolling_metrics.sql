WITH daily_transactions AS (
    SELECT
        DATE_TRUNC('day', transaction_date)::DATE AS transaction_date,
        COUNT(transaction_id) AS transaction_count,
        SUM(amount) AS total_amount
    FROM
        transactions
    WHERE
        status = 'completed'
    GROUP BY
        DATE_TRUNC('day', transaction_date)::DATE
)
SELECT
    transaction_date,
    transaction_count,
    total_amount AS daily_amount,
    ROUND(
        AVG(total_amount) OVER (
            ORDER BY transaction_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_avg_7d,
    ROUND(
        AVG(total_amount) OVER (
            ORDER BY transaction_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_avg_30d,
    ROUND(
        SUM(total_amount) OVER (
            ORDER BY transaction_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_sum_30d,
    LAG(total_amount, 1) OVER (
        ORDER BY transaction_date
    ) AS prev_day_amount,
    LEAD(total_amount, 1) OVER (
        ORDER BY transaction_date
    ) AS next_day_amount,
    ROUND(
        total_amount - LAG(total_amount, 1) OVER (
            ORDER BY transaction_date
        ),
        2
    ) AS day_over_day_change
FROM
    daily_transactions
ORDER BY
    transaction_date ASC;
