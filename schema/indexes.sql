-- Indexing customer_id on accounts to optimize customer-to-account joins
CREATE INDEX idx_accounts_customer_id ON accounts (customer_id);

-- Indexing account_id on transactions as it is a core join key
CREATE INDEX idx_transactions_account_id ON transactions (account_id);

-- Indexing merchant_id on transactions to accelerate merchant aggregation queries
CREATE INDEX idx_transactions_merchant_id ON transactions (merchant_id);

-- Indexing transaction_date for date-truncation and time-series slicing
CREATE INDEX idx_transactions_transaction_date ON transactions (transaction_date);

-- Indexing transaction status for quick filtration of failed or completed transactions
CREATE INDEX idx_transactions_status ON transactions (status);

-- Indexing transaction_id on settlements is redundant due to UNIQUE constraint, but settlement_date is indexed for time analysis
CREATE INDEX idx_settlements_settlement_date ON settlements (settlement_date);

-- Indexing flagged_date on fraud_flags to accelerate compliance audit queries
CREATE INDEX idx_fraud_flags_flagged_date ON fraud_flags (flagged_date);
