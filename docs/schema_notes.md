# Relational Schema Design & Architecture Notes

This document captures the design details and rationale for the `payments-analytics-sql` database schema, representing a real-world enterprise transactional database system.

## 1. Key Database Entities & Relationships

### Customers
- **Purpose**: Represents the core client profile.
- **Constraints**: 
  - `email` is enforced with a `UNIQUE` constraint to prevent double registrations.
  - `segment` contains a CHECK constraint restricting input to standard client categories: `retail`, `business`, or `premium`.

### Accounts
- **Purpose**: Financial accounts held by customers. One customer can have multiple accounts (e.g. current and savings accounts).
- **Constraints**:
  - `customer_id` is a foreign key with `ON DELETE CASCADE`, ensuring data is automatically cleaned if a customer profile is removed.
  - `account_type` is restricted via a CHECK constraint (`current`, `savings`, `merchant`).

### Merchants
- **Purpose**: Companies or entities accepting commercial payments.
- **Constraints**:
  - `risk_tier` is bounded (`low`, `medium`, `high`) using a CHECK constraint to enforce risk profiles.

### Transactions
- **Purpose**: The centerpiece ledger recording individual transfers, purchases, and refunds.
- **Constraints**:
  - `account_id` links directly to a customer account. If an account is deleted, transactions cascade.
  - `merchant_id` is set to `NULL` on delete (`ON DELETE SET NULL`) to retain transaction history even if a merchant is deactivated.
  - `amount` is enforced to be strictly positive (`CHECK (amount > 0)`).
  - `status` and `transaction_type` are constrained to valid processing states.

### Settlements
- **Purpose**: Payout logs for merchants. Each completed transaction is settled to the merchant minus processing fees.
- **Constraints**:
  - `transaction_id` is defined as a `UNIQUE` foreign key to enforce a strict **1:1** or **0:1** relationship (a transaction can be settled at most once).
  - Both `settled_amount` and `processing_fee` must be non-negative.

### Fraud Flags
- **Purpose**: Compliance monitoring logs. Transactions flagged as potential risk triggers are captured here.
- **Constraints**:
  - `transaction_id` is defined as a `UNIQUE` foreign key to ensure a transaction is flagged at most once.
  - `resolved_date` can be `NULL` if `is_resolved` is false.

## 2. Performance Indexes

To support complex aggregation and high-velocity analytical queries, the following indexes are applied:
1. **Foreign Key Indexes**: On `accounts(customer_id)`, `transactions(account_id)`, and `transactions(merchant_id)`. These accelerate multi-table joins during queries like merchant performance and CLV.
2. **Temporal Indexes**: On `transactions(transaction_date)` and `settlements(settlement_date)` to speed up time-series groupings, rolling windows, and cohort grouping.
3. **Categorical/Status Indexes**: On `transactions(status)` to fast-filter transactions based on their outcome.
