CREATE OR REPLACE VIEW stg_customers AS
SELECT
    CAST(customer_id AS BIGINT) AS customer_id,
    CAST(full_name AS VARCHAR) AS full_name,
    CAST(email AS VARCHAR) AS email,
    CAST(country AS VARCHAR) AS country,
    CAST(join_date AS DATE) AS join_date,
    CAST(segment AS VARCHAR) AS segment,
    CAST(is_active AS BOOLEAN) AS is_active
FROM customers;

CREATE OR REPLACE VIEW stg_accounts AS
SELECT
    CAST(account_id AS BIGINT) AS account_id,
    CAST(customer_id AS BIGINT) AS customer_id,
    CAST(account_type AS VARCHAR) AS account_type,
    CAST(currency AS VARCHAR) AS currency,
    CAST(opened_date AS DATE) AS opened_date,
    CAST(status AS VARCHAR) AS status
FROM accounts;

CREATE OR REPLACE VIEW stg_merchants AS
SELECT
    CAST(merchant_id AS BIGINT) AS merchant_id,
    CAST(merchant_name AS VARCHAR) AS merchant_name,
    CAST(category AS VARCHAR) AS category,
    CAST(country AS VARCHAR) AS country,
    CAST(registration_date AS DATE) AS registration_date,
    CAST(risk_tier AS VARCHAR) AS risk_tier
FROM merchants;

CREATE OR REPLACE VIEW stg_merchant_terms AS
SELECT
    CAST(merchant_id AS BIGINT) AS merchant_id,
    CAST(valid_from AS DATE) AS valid_from,
    CAST(valid_to AS DATE) AS valid_to,
    CAST(fee_rate_bps AS INTEGER) AS fee_rate_bps,
    CAST(settlement_sla_days AS INTEGER) AS settlement_sla_days
FROM merchant_terms;

CREATE OR REPLACE VIEW stg_transactions AS
SELECT
    CAST(transaction_id AS BIGINT) AS transaction_id,
    CAST(account_id AS BIGINT) AS account_id,
    CAST(merchant_id AS BIGINT) AS merchant_id,
    CAST(amount AS DECIMAL(15, 2)) AS amount,
    CAST(currency AS VARCHAR) AS currency,
    CAST(transaction_date AS TIMESTAMP) AS transaction_date,
    CAST(transaction_type AS VARCHAR) AS transaction_type,
    CAST(status AS VARCHAR) AS status
FROM transactions;

CREATE OR REPLACE VIEW stg_settlements AS
SELECT
    CAST(settlement_id AS BIGINT) AS settlement_id,
    CAST(transaction_id AS BIGINT) AS transaction_id,
    CAST(settlement_date AS TIMESTAMP) AS settlement_date,
    CAST(currency AS VARCHAR) AS currency,
    CAST(settled_amount AS DECIMAL(15, 2)) AS settled_amount,
    CAST(processing_fee AS DECIMAL(15, 2)) AS processing_fee,
    CAST(status AS VARCHAR) AS status
FROM settlements;

CREATE OR REPLACE VIEW stg_fraud_flags AS
SELECT
    CAST(flag_id AS BIGINT) AS flag_id,
    CAST(transaction_id AS BIGINT) AS transaction_id,
    CAST(flagged_date AS TIMESTAMP) AS flagged_date,
    CAST(flag_reason AS VARCHAR) AS flag_reason,
    CAST(is_resolved AS BOOLEAN) AS is_resolved,
    CAST(resolved_date AS TIMESTAMP) AS resolved_date
FROM fraud_flags;
