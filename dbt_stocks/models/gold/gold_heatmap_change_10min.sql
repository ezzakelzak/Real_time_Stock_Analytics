SELECT
    symbol,
    ROUND(((MAX(current_price) - MIN(current_price)) / NULLIF(MIN(current_price), 0)) * 100, 2) AS change_percent_10min
FROM {{ ref('silver_clean_stock_quotes') }}
WHERE market_timestamp >= DATEADD('minute', -10, CURRENT_TIMESTAMP())
GROUP BY symbol
