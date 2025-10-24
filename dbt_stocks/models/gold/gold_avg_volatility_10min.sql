WITH source AS (
  SELECT
    symbol,
    TRY_CAST(current_price AS DOUBLE) AS current_price_dbl,
    TO_TIMESTAMP_LTZ(market_timestamp) AS ts
  FROM {{ ref('silver_clean_stock_quotes') }}
  WHERE TRY_CAST(current_price AS DOUBLE) IS NOT NULL
),

latest_window AS (
  
  SELECT
    DATE_TRUNC('minute', MAX(ts)) AS max_time
  FROM source
),

latest_prices AS (
  SELECT
    symbol,
    AVG(current_price_dbl) AS avg_price_10min
  FROM source
  JOIN latest_window lw
    ON ts BETWEEN lw.max_time - INTERVAL '10 minutes' AND lw.max_time
  GROUP BY symbol
),

all_time_volatility AS (
  SELECT
    symbol,
    STDDEV_POP(current_price_dbl) AS volatility,
    CASE
      WHEN AVG(current_price_dbl) = 0 THEN NULL
      ELSE STDDEV_POP(current_price_dbl) / NULLIF(AVG(current_price_dbl), 0)
    END AS relative_volatility
  FROM source
  GROUP BY symbol
)

SELECT
  lp.symbol,
  lp.avg_price_10min,
  v.volatility,
  v.relative_volatility
FROM latest_prices lp
JOIN all_time_volatility v ON lp.symbol = v.symbol
ORDER BY lp.symbol
