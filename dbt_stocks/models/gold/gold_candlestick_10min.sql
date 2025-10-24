WITH enriched AS (
    SELECT
        symbol,
        DATE_TRUNC('minute', market_timestamp) AS minute_mark,
        FLOOR(EXTRACT(minute FROM market_timestamp) / 10) AS minute_bucket,
        DATE_TRUNC('hour', market_timestamp) AS hour_mark,
        day_low,
        day_high,
        current_price,
        FIRST_VALUE(current_price) OVER (
            PARTITION BY symbol, hour_mark, minute_bucket
            ORDER BY market_timestamp
        ) AS candle_open,
        LAST_VALUE(current_price) OVER (
            PARTITION BY symbol, hour_mark, minute_bucket
            ORDER BY market_timestamp
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS candle_close
    FROM {{ ref('silver_clean_stock_quotes') }}
),

candles AS (
    SELECT
        symbol,
        DATEADD(minute, minute_bucket * 10, hour_mark) AS candle_time,
        MIN(day_low) AS candle_low,
        MAX(day_high) AS candle_high,
        ANY_VALUE(candle_open) AS candle_open,
        ANY_VALUE(candle_close) AS candle_close,
        AVG(current_price) AS trend_line
    FROM enriched
    GROUP BY symbol, hour_mark, minute_bucket
),

ranked AS (
    SELECT
        c.*,
        ROW_NUMBER() OVER (
            PARTITION BY symbol
            ORDER BY candle_time DESC
        ) AS rn
    FROM candles c
)

SELECT
    symbol,
    candle_time,
    candle_low,
    candle_high,
    candle_open,
    candle_close,
    trend_line
FROM ranked
WHERE rn <= 12
ORDER BY symbol, candle_time
