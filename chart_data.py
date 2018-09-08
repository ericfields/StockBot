import pandas as pd
from multiprocessing.pool import ThreadPool
from dateutil import parser as dateparser
from robinhood import Quote, Historicals

# Certain chart spans can only be used with certain data intervals.
# This defines each interval to its highest logical resolution.
SPAN_INTERVALS = {
    'day': '5minute',
    'week': '10minute',
    'year': 'day',
    '5year': 'week',
    'all': 'week'
}

class ChartData():
    def __init__(self, instrument, span="day"):
        self.symbol = instrument.symbol
        self.company_name = instrument.simple_name or instrument.name

        pool = ThreadPool(processes=1)
        quote_thread_result = pool.apply_async(Quote.get, (instrument.symbol,))

        interval = SPAN_INTERVALS[span]

        options = {
            'interval': interval
        }
        if span != 'all':
            options['span'] = span
        if span == 'day':
            options['bounds'] = 'trading'
        historicals = Historicals.list(instrument.symbol, **options)

        time_values = []
        price_values = []
        for historical in historicals:
            time_values.append(dateparser.parse(historical.begins_at))
            price_values.append(float(historical.close_price))

        if historicals.previous_close_price:
            last_closing_price = float(historicals.previous_close_price)
        else:
            last_closing_price = float(historicals.items[0].close_price)

        quote = quote_thread_result.get()
        current_price = float(quote.last_trade_price)

        self.series = pd.Series(price_values, index=time_values)
        self.last_closing_price = last_closing_price
        self.current_price = current_price
        self.span = span
