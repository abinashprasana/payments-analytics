CREATE OR REPLACE VIEW int_expected_settlements AS
WITH eligible AS (
    SELECT
        tx.transaction_id AS payment_id,
        tx.transaction_id,
        tx.account_id,
        tx.merchant_id,
        m.merchant_name,
        m.category AS merchant_category,
        tx.transaction_date,
        CAST(tx.transaction_date AS DATE) AS close_date,
        tx.transaction_type,
        tx.status AS transaction_status,
        tx.currency AS transaction_currency,
        tx.amount AS gross_amount,
        CAST(ROUND(tx.amount * 100, 0) AS BIGINT) AS gross_minor_units,
        mt.valid_from AS term_valid_from,
        mt.valid_to AS term_valid_to,
        mt.fee_rate_bps,
        mt.settlement_sla_days,
        ctx.as_of_date AS analysis_as_of_date
    FROM stg_transactions AS tx
    CROSS JOIN analytics_context AS ctx
    INNER JOIN stg_merchants AS m
        ON m.merchant_id = tx.merchant_id
    INNER JOIN stg_merchant_terms AS mt
        ON mt.merchant_id = tx.merchant_id
        AND CAST(tx.transaction_date AS DATE) >= mt.valid_from
        AND (
            mt.valid_to IS NULL
            OR CAST(tx.transaction_date AS DATE) <= mt.valid_to
        )
    WHERE tx.transaction_type = 'purchase'
      AND tx.status = 'completed'
      AND tx.merchant_id IS NOT NULL
      AND CAST(tx.transaction_date AS DATE) <= ctx.as_of_date
), fee_products AS (
    SELECT
        eligible.*,
        gross_minor_units * CAST(fee_rate_bps AS BIGINT) AS fee_product
    FROM eligible
), priced AS (
    SELECT
        fee_products.*,
        CAST(
            (
                fee_product - MOD(fee_product, CAST(10000 AS BIGINT))
            ) / CAST(10000 AS BIGINT)
            AS BIGINT
        )
        + CASE
            WHEN MOD(fee_product, CAST(10000 AS BIGINT)) >= 5000 THEN 1
            ELSE 0
          END AS expected_fee_minor_units
    FROM fee_products
)
SELECT
    payment_id,
    transaction_id,
    account_id,
    merchant_id,
    merchant_name,
    merchant_category,
    transaction_date,
    close_date,
    transaction_type,
    transaction_status,
    transaction_currency,
    gross_amount,
    gross_minor_units,
    term_valid_from,
    term_valid_to,
    fee_rate_bps,
    settlement_sla_days,
    analysis_as_of_date,
    close_date + settlement_sla_days AS expected_settlement_date,
    CAST(
        CAST(expected_fee_minor_units AS DECIMAL(15, 2))
        * CAST(0.01 AS DECIMAL(3, 2))
        AS DECIMAL(15, 2)
    ) AS expected_fee,
    expected_fee_minor_units,
    CAST(
        CAST(gross_minor_units - expected_fee_minor_units AS DECIMAL(15, 2))
        * CAST(0.01 AS DECIMAL(3, 2))
        AS DECIMAL(15, 2)
    ) AS expected_settled_amount,
    gross_minor_units - expected_fee_minor_units AS expected_settled_minor_units
FROM priced;
