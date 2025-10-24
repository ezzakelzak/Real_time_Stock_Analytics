WITH diffs AS (
  SELECT
    symbol,
    market_timestamp,
    current_price,
    current_price - LAG(current_price) OVER (
      PARTITION BY symbol
      ORDER BY market_timestamp
    ) AS diff
  FROM {{ ref('silver_clean_stock_quotes') }}
),

gains_losses AS (
  SELECT
    symbol,
    market_timestamp,
    CASE WHEN diff > 0 THEN diff ELSE 0 END AS gain,
    CASE WHEN diff < 0 THEN ABS(diff) ELSE 0 END AS loss
  FROM diffs
),

rsi_calc AS (
  SELECT
    symbol,
    market_timestamp,
    AVG(gain) OVER (
      PARTITION BY symbol
      ORDER BY market_timestamp
      ROWS BETWEEN 10 PRECEDING AND CURRENT ROW
    ) AS avg_gain,
    AVG(loss) OVER (
      PARTITION BY symbol
      ORDER BY market_timestamp
      ROWS BETWEEN 10 PRECEDING AND CURRENT ROW
    ) AS avg_loss
  FROM gains_losses
)

SELECT
  symbol,
  market_timestamp,
  CASE
    WHEN avg_loss = 0 THEN 100
    ELSE 100 - (100 / (1 + (avg_gain / avg_loss)))
  END AS rsi
FROM rsi_calc
ORDER BY symbol, market_timestamp
