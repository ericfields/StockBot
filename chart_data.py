import pandas as pd
from multiprocessing.pool import ThreadPool
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from robinhood import Quote, Historicals

# Certain chart spans can only be used with certain data intervals.
# This defines each interval to its highest logical resolution.

class ChartData():
    def __init__(self, instrument, span=timedelta(days=1)):
        self.symbol = instrument.symbol
        self.security_name = instrument.simple_name or instrument.name

        pool = ThreadPool(processes=1)
        quote_thread_result = pool.apply_async(Quote.get, (instrument.symbol,))

        historicals_options = self.__historical_params(instrument, span)

        historicals = Historicals.list(instrument.symbol, **historicals_options)

        quote = quote_thread_result.get()
        current_price = quote.last_extended_hours_trade_price or quote.last_trade_price

        start_date = max(datetime.now() - span, instrument.list_date)

        time_values = []
        price_values = []
        for historical in historicals:
            # Exclude data before our requested start date
            if historical.begins_at < start_date:
                continue

            time_values.append(historical.begins_at)
            price_values.append(historical.close_price)

        # There is a chance that we are viewing this graph right at pre-market open,
        # in which case historicals will be empty. Add the current price
        # to the series instead.
        if len(time_values) == 0:
            time_values.append(datetime.now())
            price_values.append(current_price)

        if historicals.previous_close_price:
            initial_price = historicals.previous_close_price
        else:
            initial_price = historicals.items[0].open_price

        self.series = pd.Series(price_values, index=time_values)
        self.initial_price = initial_price
        self.current_price = current_price
        self.span = span

    def __historical_params(self, instrument, span):
        now = datetime.now()

        # If the security was listed after our requested span begins,
        # we reduce the span to when the security was listed
        if now - span < instrument.list_date:
            span = now - instrument.list_date

        bounds = None

        # Robinhood only has a few options for requesting a span of historical
        # Determine the minimum span of data we can request from Robinhood
        if span <= timedelta(days=1):
            request_span = 'day'
            # Need to set request bounds to all trading hours as well
            bounds = 'trading'
        elif span <= timedelta(days=7):
            request_span = 'week'
        elif span <= timedelta(days=365):
            request_span = 'year'
        elif span <= timedelta(days=365*5):
            request_span = '5year'
        else:
            # Do not set the request span. Equivalent to 'all'
            request_span = None

        options = {'interval': self.__interval_for_span(span)}
        if request_span:
            options['span'] = request_span
        if bounds:
            options['bounds'] = bounds

        return options

    # Determine the interval of data that we should request from Robinhood
    # given the required data span
    def __interval_for_span(self, span):
        if span <= timedelta(days=1):
            return '5minute'
        elif span <= timedelta(days=7):
            return '10minute'
        elif span <= timedelta(days=365):
            return 'day'
        else:
            return 'week'
