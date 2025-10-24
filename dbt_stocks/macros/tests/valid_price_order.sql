{% test valid_price_order(model) %}

select *
from {{ model }}
where not (
    candle_low <= candle_open
    and candle_open <= candle_high
    and candle_low <= candle_close
    and candle_close <= candle_high
)

{% endtest %}
