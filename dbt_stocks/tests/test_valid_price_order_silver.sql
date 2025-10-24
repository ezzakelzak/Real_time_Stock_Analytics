-- Test: verify price consistency in silver_clean_stock_quotes
select *
from {{ ref('silver_clean_stock_quotes') }}
where 
    day_low > day_high
    or day_open > day_high
    or prev_close > day_high
    or day_low > day_open
    or day_low > prev_close