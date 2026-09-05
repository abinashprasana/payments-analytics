CREATE OR REPLACE VIEW mart_benford_conformity AS
WITH expected AS (
    SELECT
        leading_digit,
        CAST(LOG10(1 + 1.0 / leading_digit) * 100 AS DECIMAL(12, 6)) AS expected_pct
    FROM (VALUES (1), (2), (3), (4), (5), (6), (7), (8), (9)) AS d(leading_digit)
), observed AS (
    SELECT
        transaction_currency AS currency,
        CAST(SUBSTRING(CAST(gross_minor_units AS VARCHAR), 1, 1) AS INTEGER)
            AS leading_digit,
        COUNT(*) AS observed_count
    FROM int_settlement_reconciliation
    WHERE gross_minor_units > 0
    GROUP BY
        transaction_currency,
        CAST(SUBSTRING(CAST(gross_minor_units AS VARCHAR), 1, 1) AS INTEGER)
), totals AS (
    SELECT currency, SUM(observed_count) AS total_count
    FROM observed
    GROUP BY currency
), digits AS (
    SELECT
        t.currency,
        t.total_count,
        e.leading_digit,
        e.expected_pct,
        COALESCE(o.observed_count, 0) AS observed_count
    FROM totals AS t
    CROSS JOIN expected AS e
    LEFT JOIN observed AS o
        ON o.currency = t.currency AND o.leading_digit = e.leading_digit
), scored AS (
    SELECT
        digits.*,
        CAST(observed_count AS DECIMAL(12, 6)) * 100 / total_count AS observed_pct,
        CAST(total_count AS DECIMAL(18, 6)) * expected_pct / 100 AS expected_count
    FROM digits
), currency_stats AS (
    SELECT
        currency,
        CAST(
            SUM(POWER(observed_count - expected_count, 2) / expected_count)
            AS DECIMAL(18, 6)
        ) AS chi_square_stat,
        CAST(AVG(ABS(observed_pct - expected_pct)) / 100 AS DECIMAL(12, 8)) AS mad_stat
    FROM scored
    GROUP BY currency
)
SELECT
    s.currency,
    s.leading_digit,
    s.observed_count,
    s.observed_pct,
    s.expected_pct,
    s.total_count,
    c.chi_square_stat,
    c.mad_stat
FROM scored AS s
INNER JOIN currency_stats AS c
    ON c.currency = s.currency;
