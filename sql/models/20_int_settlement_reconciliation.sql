CREATE OR REPLACE VIEW int_settlement_reconciliation AS
WITH joined AS (
    SELECT
        e.*,
        s.settlement_id,
        s.settlement_date AS actual_settlement_date,
        s.currency AS settlement_currency,
        s.settled_amount AS recorded_settled_amount,
        s.processing_fee AS recorded_fee,
        s.status AS settlement_status,
        CAST(ROUND(s.settled_amount * 100, 0) AS BIGINT)
            AS recorded_settled_minor_units,
        CAST(ROUND(s.processing_fee * 100, 0) AS BIGINT)
            AS recorded_fee_minor_units,
        CAST(ROUND((s.settled_amount + s.processing_fee) * 100, 0) AS BIGINT)
            AS recorded_gross_minor_units,
        f.flag_id AS fraud_flag_id,
        f.flag_reason AS fraud_reason,
        CASE
            WHEN f.resolved_date IS NOT NULL
             AND CAST(f.resolved_date AS DATE) <= e.analysis_as_of_date
                THEN TRUE
            WHEN f.flag_id IS NOT NULL THEN FALSE
            ELSE NULL
        END AS fraud_is_resolved,
        CASE
            WHEN f.resolved_date IS NOT NULL
             AND CAST(f.resolved_date AS DATE) <= e.analysis_as_of_date
                THEN f.resolved_date
            ELSE NULL
        END AS fraud_resolved_date
    FROM int_expected_settlements AS e
    LEFT JOIN stg_settlements AS s
        ON s.transaction_id = e.transaction_id
       AND CAST(s.settlement_date AS DATE) <= e.analysis_as_of_date
    LEFT JOIN stg_fraud_flags AS f
        ON f.transaction_id = e.transaction_id
       AND CAST(f.flagged_date AS DATE) <= e.analysis_as_of_date
), flags AS (
    SELECT
        joined.*,
        (
            settlement_id IS NULL
            AND expected_settlement_date < analysis_as_of_date
        ) AS is_missing,
        (
            settlement_id IS NOT NULL
            AND settlement_currency <> transaction_currency
        ) AS is_currency_mismatch,
        (
            settlement_id IS NOT NULL
            AND settlement_currency = transaction_currency
            AND ABS(gross_minor_units - recorded_gross_minor_units) > 1
        ) AS is_amount_mismatch,
        (
            settlement_id IS NOT NULL
            AND settlement_currency = transaction_currency
            AND ABS(recorded_fee_minor_units - expected_fee_minor_units) > 1
        ) AS is_fee_mismatch,
        (
            settlement_id IS NOT NULL
            AND CAST(actual_settlement_date AS DATE) > expected_settlement_date
        ) AS is_late,
        (settlement_status = 'disputed') AS is_disputed,
        (
            (settlement_id IS NULL AND expected_settlement_date < analysis_as_of_date)
            OR (
                settlement_id IS NOT NULL
                AND CAST(actual_settlement_date AS DATE) > expected_settlement_date
            )
        ) AS is_sla_breach
    FROM joined
), classified AS (
    SELECT
        flags.*,
        CASE
            WHEN is_missing THEN 'missing'
            WHEN is_currency_mismatch THEN 'currency_mismatch'
            WHEN is_amount_mismatch THEN 'amount_mismatch'
            WHEN is_fee_mismatch THEN 'fee_mismatch'
            WHEN is_late THEN 'late'
            WHEN is_disputed THEN 'disputed'
            ELSE 'matched'
        END AS primary_reason,
        RTRIM(
            CASE WHEN is_missing THEN 'missing,' ELSE '' END
            || CASE WHEN is_currency_mismatch THEN 'currency_mismatch,' ELSE '' END
            || CASE WHEN is_amount_mismatch THEN 'amount_mismatch,' ELSE '' END
            || CASE WHEN is_fee_mismatch THEN 'fee_mismatch,' ELSE '' END
            || CASE WHEN is_late THEN 'late,' ELSE '' END
            || CASE WHEN is_disputed THEN 'disputed,' ELSE '' END,
            ','
        ) AS exception_reasons
    FROM flags
)
SELECT
    classified.*,
    (
        settlement_id IS NOT NULL
        AND settlement_currency = transaction_currency
        AND ABS(gross_minor_units - recorded_gross_minor_units) <= 1
    ) AS is_match,
    CASE
        WHEN settlement_id IS NULL AND expected_settlement_date < analysis_as_of_date
            THEN analysis_as_of_date - expected_settlement_date
        WHEN settlement_id IS NOT NULL
             AND CAST(actual_settlement_date AS DATE) > expected_settlement_date
            THEN CAST(actual_settlement_date AS DATE) - expected_settlement_date
        ELSE 0
    END AS days_overdue,
    CASE
        WHEN settlement_id IS NOT NULL AND settlement_currency = transaction_currency
            THEN recorded_fee_minor_units - expected_fee_minor_units
        ELSE NULL
    END AS fee_delta_minor_units
FROM classified;
