DROP TABLE IF EXISTS fraud_flags CASCADE;
DROP TABLE IF EXISTS settlements CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS merchant_terms CASCADE;
DROP TABLE IF EXISTS merchants CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    country VARCHAR(100) NOT NULL,
    join_date DATE NOT NULL,
    segment VARCHAR(20) NOT NULL CHECK (segment IN ('retail', 'business', 'premium')),
    is_active BOOLEAN NOT NULL
);

CREATE TABLE accounts (
    account_id INT PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('current', 'savings', 'merchant')),
    currency VARCHAR(3) NOT NULL CHECK (currency IN ('EUR', 'GBP', 'AUD', 'CAD')),
    opened_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'closed', 'suspended'))
);

CREATE TABLE merchants (
    merchant_id INT PRIMARY KEY,
    merchant_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN (
        'Retail', 'Travel', 'Entertainment', 'Electronics', 'Utilities',
        'Food & Beverage', 'Services', 'Healthcare'
    )),
    country VARCHAR(100) NOT NULL,
    registration_date DATE NOT NULL,
    risk_tier VARCHAR(20) NOT NULL CHECK (risk_tier IN ('low', 'medium', 'high'))
);

CREATE TABLE merchant_terms (
    merchant_id INT NOT NULL REFERENCES merchants (merchant_id) ON DELETE CASCADE,
    valid_from DATE NOT NULL,
    valid_to DATE,
    fee_rate_bps INT NOT NULL CHECK (fee_rate_bps BETWEEN 0 AND 10000),
    settlement_sla_days INT NOT NULL CHECK (settlement_sla_days BETWEEN 1 AND 30),
    PRIMARY KEY (merchant_id, valid_from),
    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

CREATE TABLE transactions (
    transaction_id INT PRIMARY KEY,
    account_id INT NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    merchant_id INT REFERENCES merchants (merchant_id) ON DELETE RESTRICT,
    amount NUMERIC(15, 2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL CHECK (currency IN ('EUR', 'GBP', 'AUD', 'CAD')),
    transaction_date TIMESTAMP NOT NULL,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('purchase', 'refund', 'transfer')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('completed', 'pending', 'failed')),
    CHECK (
        (transaction_type = 'transfer' AND merchant_id IS NULL)
        OR (transaction_type IN ('purchase', 'refund') AND merchant_id IS NOT NULL)
    )
);

CREATE TABLE settlements (
    settlement_id INT PRIMARY KEY,
    transaction_id INT UNIQUE NOT NULL REFERENCES transactions (transaction_id) ON DELETE CASCADE,
    settlement_date TIMESTAMP NOT NULL,
    currency VARCHAR(3) NOT NULL CHECK (currency IN ('EUR', 'GBP', 'AUD', 'CAD')),
    settled_amount NUMERIC(15, 2) NOT NULL CHECK (settled_amount >= 0),
    processing_fee NUMERIC(15, 2) NOT NULL CHECK (processing_fee >= 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('settled', 'delayed', 'disputed'))
);

CREATE TABLE fraud_flags (
    flag_id INT PRIMARY KEY,
    transaction_id INT UNIQUE NOT NULL REFERENCES transactions (transaction_id) ON DELETE CASCADE,
    flagged_date TIMESTAMP NOT NULL,
    flag_reason VARCHAR(255) NOT NULL,
    is_resolved BOOLEAN NOT NULL,
    resolved_date TIMESTAMP,
    CHECK (
        (is_resolved AND resolved_date IS NOT NULL AND resolved_date >= flagged_date)
        OR (NOT is_resolved AND resolved_date IS NULL)
    )
);
