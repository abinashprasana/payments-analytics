CREATE OR REPLACE VIEW mart_category_health AS
WITH category_rollup AS (
    SELECT
        merchant_category,
        close_date,
        transaction_currency AS currency,
        COUNT(*) AS eligible_count,
        SUM(CASE WHEN is_match THEN 1 ELSE 0 END) AS matched_count,
        SUM(CASE WHEN primary_reason <> 'matched' THEN 1 ELSE 0 END) AS exception_count,
        SUM(CASE WHEN is_missing THEN 1 ELSE 0 END) AS missing_count,
        SUM(CASE WHEN is_currency_mismatch THEN 1 ELSE 0 END) AS currency_mismatch_count,
        SUM(CASE WHEN is_amount_mismatch THEN 1 ELSE 0 END) AS amount_mismatch_count,
        SUM(CASE WHEN is_fee_mismatch THEN 1 ELSE 0 END) AS fee_mismatch_count,
        SUM(CASE WHEN is_late THEN 1 ELSE 0 END) AS late_count,
        SUM(CASE WHEN is_disputed THEN 1 ELSE 0 END) AS disputed_count,
        SUM(CASE WHEN is_sla_breach THEN gross_minor_units ELSE 0 END)
            AS overdue_minor_units,
        SUM(COALESCE(fee_delta_minor_units, 0)) AS fee_delta_minor_units
    FROM int_settlement_reconciliation
    GROUP BY merchant_category, close_date, transaction_currency
)
SELECT
    category_rollup.*,
    CAST(
        exception_count * 1.0 / NULLIF(eligible_count, 0)
        AS DECIMAL(12, 6)
    ) AS exception_rate,
    CASE
        WHEN missing_count > 0 THEN 'missing'
        WHEN currency_mismatch_count > 0 THEN 'currency_mismatch'
        WHEN amount_mismatch_count > 0 THEN 'amount_mismatch'
        WHEN fee_mismatch_count > 0 THEN 'fee_mismatch'
        WHEN late_count > 0 THEN 'late'
        WHEN disputed_count > 0 THEN 'disputed'
        ELSE 'matched'
    END AS primary_reason
FROM category_rollup;
