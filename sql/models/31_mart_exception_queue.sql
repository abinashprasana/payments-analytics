CREATE OR REPLACE VIEW mart_exception_queue AS
SELECT
    payment_id,
    transaction_id,
    transaction_date,
    transaction_currency AS currency,
    gross_minor_units,
    merchant_id,
    merchant_name,
    merchant_category,
    expected_settlement_date,
    actual_settlement_date,
    days_overdue,
    primary_reason,
    exception_reasons,
    is_missing,
    is_currency_mismatch,
    is_amount_mismatch,
    is_fee_mismatch,
    is_late,
    is_disputed,
    is_sla_breach,
    recorded_fee_minor_units,
    expected_fee_minor_units,
    fee_delta_minor_units,
    CASE primary_reason
        WHEN 'missing' THEN 1
        WHEN 'currency_mismatch' THEN 2
        WHEN 'amount_mismatch' THEN 3
        WHEN 'fee_mismatch' THEN 4
        WHEN 'late' THEN 5
        WHEN 'disputed' THEN 6
        ELSE 7
    END AS priority_rank
FROM int_settlement_reconciliation
WHERE primary_reason <> 'matched';
