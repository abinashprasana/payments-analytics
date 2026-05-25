-- Compute daily processing velocity, rolling averages, and lead/lag differences to capture daily shifts
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
    -- Calculate 7-day rolling average transaction amount
    ROUND(
        AVG(total_amount) OVER (
            ORDER BY transaction_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_avg_7d,
    -- Calculate 30-day rolling average transaction amount
    ROUND(
        AVG(total_amount) OVER (
            ORDER BY transaction_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_avg_30d,
    -- Calculate 30-day rolling cumulative sum of transaction amount
    ROUND(
        SUM(total_amount) OVER (
            ORDER BY transaction_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_sum_30d,
    -- Fetch the previous day's value to calculate change
    LAG(total_amount, 1) OVER (
        ORDER BY transaction_date
    ) AS prev_day_amount,
    -- Fetch the next day's value to show predictive trend
    LEAD(total_amount, 1) OVER (
        ORDER BY transaction_date
    ) AS next_day_amount,
    -- Compute day-over-day raw variance in total amount
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
