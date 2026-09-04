CREATE INDEX idx_accounts_customer_id ON accounts (customer_id);

CREATE INDEX idx_transactions_account_id ON transactions (account_id);

CREATE INDEX idx_transactions_merchant_id ON transactions (merchant_id);

CREATE INDEX idx_transactions_transaction_date ON transactions (transaction_date);

CREATE INDEX idx_transactions_status ON transactions (status);

CREATE INDEX idx_merchant_terms_effective
    ON merchant_terms (merchant_id, valid_from, valid_to);

CREATE INDEX idx_settlements_settlement_date ON settlements (settlement_date);

CREATE INDEX idx_settlements_currency ON settlements (currency);

CREATE INDEX idx_fraud_flags_flagged_date ON fraud_flags (flagged_date);
