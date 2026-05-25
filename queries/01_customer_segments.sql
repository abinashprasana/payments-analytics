-- Analyze customer distribution across countries and tier segments to focus regional marketing
SELECT
    country,
    segment,
    COUNT(customer_id) AS customer_count
FROM
    customers
GROUP BY
    country,
    segment
HAVING
    COUNT(customer_id) > 10
ORDER BY
    customer_count DESC;
