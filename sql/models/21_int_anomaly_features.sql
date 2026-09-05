CREATE OR REPLACE VIEW int_anomaly_features AS
WITH deltas AS (
    SELECT
        r.*,
        r.recorded_gross_minor_units - r.gross_minor_units AS amount_delta_minor_units,
        CAST(EXTRACT(dow FROM r.transaction_date) AS INTEGER) AS transaction_dow
    FROM int_settlement_reconciliation AS r
), rolling AS (
    SELECT
        deltas.*,
        CAST(AVG(days_overdue) OVER merchant_history AS DECIMAL(12, 6))
            AS merchant_rolling_avg_delay_days,
        CAST(AVG(amount_delta_minor_units) OVER merchant_history AS DECIMAL(18, 6))
            AS merchant_rolling_avg_amount_delta
    FROM deltas
    WINDOW merchant_history AS (
        PARTITION BY merchant_id
        ORDER BY transaction_date, payment_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    )
)
SELECT
    payment_id,
    transaction_id,
    merchant_id,
    merchant_name,
    merchant_category,
    transaction_date,
    transaction_currency,
    gross_minor_units,
    days_overdue AS settlement_delay_days,
    fee_delta_minor_units,
    amount_delta_minor_units,
    is_currency_mismatch,
    transaction_dow,
    merchant_rolling_avg_delay_days,
    merchant_rolling_avg_amount_delta,
    (days_overdue - merchant_rolling_avg_delay_days) AS delay_vs_merchant_avg,
    (amount_delta_minor_units - merchant_rolling_avg_amount_delta)
        AS amount_delta_vs_merchant_avg,
    primary_reason,
    is_match,
    analysis_as_of_date
FROM rolling;
