SELECT
    symbol,
    current_price,
    change_amount,
    change_percent
FROM (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY fetched_at DESC) AS rn
    FROM {{ ref('silver_clean_stock_quotes') }}
) t
WHERE rn = 1
