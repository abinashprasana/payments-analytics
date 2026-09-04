CREATE OR REPLACE VIEW mart_daily_close AS
SELECT
    close_date,
    transaction_currency AS currency,
    COUNT(*) AS eligible_count,
    SUM(CASE WHEN is_match THEN 1 ELSE 0 END) AS matched_count,
    SUM(CASE WHEN primary_reason <> 'matched' THEN 1 ELSE 0 END) AS exception_count,
    CAST(
        SUM(CASE WHEN is_match THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0)
        AS DECIMAL(12, 6)
    ) AS coverage_rate,
    SUM(gross_minor_units) AS gross_minor_units,
    SUM(CASE
        WHEN settlement_currency = transaction_currency
            THEN COALESCE(recorded_settled_minor_units, 0)
        ELSE 0
    END) AS settled_minor_units,
    SUM(CASE WHEN is_sla_breach THEN gross_minor_units ELSE 0 END) AS overdue_minor_units,
    SUM(COALESCE(fee_delta_minor_units, 0)) AS fee_delta_minor_units,
    SUM(CASE WHEN is_missing THEN 1 ELSE 0 END) AS missing_count,
    SUM(CASE WHEN is_missing THEN gross_minor_units ELSE 0 END) AS missing_minor_units,
    SUM(CASE WHEN is_currency_mismatch THEN 1 ELSE 0 END) AS currency_mismatch_count,
    SUM(CASE WHEN is_currency_mismatch THEN gross_minor_units ELSE 0 END)
        AS currency_mismatch_minor_units,
    SUM(CASE WHEN is_amount_mismatch THEN 1 ELSE 0 END) AS amount_mismatch_count,
    SUM(CASE WHEN is_amount_mismatch THEN gross_minor_units ELSE 0 END)
        AS amount_mismatch_minor_units,
    SUM(CASE WHEN is_fee_mismatch THEN 1 ELSE 0 END) AS fee_mismatch_count,
    SUM(CASE WHEN is_fee_mismatch THEN gross_minor_units ELSE 0 END)
        AS fee_mismatch_minor_units,
    SUM(CASE WHEN is_late THEN 1 ELSE 0 END) AS late_count,
    SUM(CASE WHEN is_late THEN gross_minor_units ELSE 0 END) AS late_minor_units,
    SUM(CASE WHEN is_disputed THEN 1 ELSE 0 END) AS disputed_count,
    SUM(CASE WHEN is_disputed THEN gross_minor_units ELSE 0 END) AS disputed_minor_units,
    SUM(CASE WHEN is_sla_breach THEN 1 ELSE 0 END) AS sla_breach_count
FROM int_settlement_reconciliation
GROUP BY close_date, transaction_currency;
