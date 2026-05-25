-- Dropping tables if they exist to support clean re-runs
DROP TABLE IF EXISTS fraud_flags CASCADE;
DROP TABLE IF EXISTS settlements CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS merchants CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- Holds core profile and segment details of our customers
CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    country VARCHAR(100) NOT NULL,
    join_date DATE NOT NULL,
    segment VARCHAR(20) NOT NULL CHECK (segment IN ('retail', 'business', 'premium')),
    is_active BOOLEAN NOT NULL
);

-- Stores customer-owned accounts, supporting multi-currency setups
CREATE TABLE accounts (
    account_id INT PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('current', 'savings', 'merchant')),
    currency VARCHAR(3) NOT NULL,
    opened_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL
);

-- Contains profiles for registered payment-accepting merchant entities
CREATE TABLE merchants (
    merchant_id INT PRIMARY KEY,
    merchant_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    country VARCHAR(100) NOT NULL,
    registration_date DATE NOT NULL,
    risk_tier VARCHAR(20) NOT NULL CHECK (risk_tier IN ('low', 'medium', 'high'))
);

-- Tracks transaction processing details across accounts and merchants
CREATE TABLE transactions (
    transaction_id INT PRIMARY KEY,
    account_id INT NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    merchant_id INT REFERENCES merchants (merchant_id) ON DELETE SET NULL,
    amount NUMERIC(15, 2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL,
    transaction_date TIMESTAMP NOT NULL,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('purchase', 'refund', 'transfer')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('completed', 'pending', 'failed'))
);

-- Captures payout settlements and fees for merchant acquisitions
CREATE TABLE settlements (
    settlement_id INT PRIMARY KEY,
    transaction_id INT UNIQUE NOT NULL REFERENCES transactions (transaction_id) ON DELETE CASCADE,
    settlement_date TIMESTAMP NOT NULL,
    settled_amount NUMERIC(15, 2) NOT NULL CHECK (settled_amount >= 0),
    processing_fee NUMERIC(15, 2) NOT NULL CHECK (processing_fee >= 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('settled', 'delayed', 'disputed'))
);

-- Holds compliance-flagged events for transaction fraud surveillance
CREATE TABLE fraud_flags (
    flag_id INT PRIMARY KEY,
    transaction_id INT UNIQUE NOT NULL REFERENCES transactions (transaction_id) ON DELETE CASCADE,
    flagged_date TIMESTAMP NOT NULL,
    flag_reason VARCHAR(255) NOT NULL,
    is_resolved BOOLEAN NOT NULL,
    resolved_date TIMESTAMP
);
