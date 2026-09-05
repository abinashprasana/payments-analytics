CREATE OR REPLACE VIEW mart_quality_screens AS
WITH daily AS (
    SELECT
        close_date,
        currency,
        eligible_count,
        exception_count,
        CAST(exception_count AS DECIMAL(12, 6)) / NULLIF(eligible_count, 0)
            AS exception_rate
    FROM mart_daily_close
), rolling AS (
    SELECT
        daily.*,
        CAST(AVG(exception_rate) OVER baseline AS DECIMAL(12, 6))
            AS rolling_mean_exception_rate,
        CAST(STDDEV_SAMP(exception_rate) OVER baseline AS DECIMAL(12, 6))
            AS rolling_stddev_exception_rate,
        COUNT(*) OVER baseline AS baseline_days
    FROM daily
    WINDOW baseline AS (
        PARTITION BY currency
        ORDER BY close_date
        ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
    )
), limits AS (
    SELECT
        rolling.*,
        CASE
            WHEN baseline_days < 6 THEN NULL
            ELSE rolling_mean_exception_rate + 3 * rolling_stddev_exception_rate
        END AS control_limit_upper
    FROM rolling
)
SELECT
    close_date,
    currency,
    eligible_count,
    exception_count,
    exception_rate,
    baseline_days,
    rolling_mean_exception_rate,
    rolling_stddev_exception_rate,
    control_limit_upper,
    CASE
        WHEN control_limit_upper IS NULL OR rolling_stddev_exception_rate = 0
            THEN NULL
        ELSE CAST(
            (exception_rate - rolling_mean_exception_rate)
            / rolling_stddev_exception_rate
            AS DECIMAL(12, 6)
        )
    END AS z_score,
    (exception_rate > control_limit_upper) AS breached
FROM limits;
