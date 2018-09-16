import pandas as pd
from chart_data import ChartData
from multiprocessing.pool import ThreadPool
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from robinhood.models import Quote, Historicals, OptionQuote, OptionHistoricals

class RobinhoodChartData(ChartData):

    @staticmethod
    def call_async(method, *args):
        pool = ThreadPool(processes=1)
        return pool.apply_async(method, tuple(args))

    @staticmethod
    def historical_params(start_date, span):
        now = datetime.now()

        # If the security was listed after our requested span begins,
        # we reduce the span to when the security was listed
        if now - span < start_date:
            span = now - start_date

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

        options = {'interval': RobinhoodChartData.interval_for_span(span)}
        if request_span:
            options['span'] = request_span
        if bounds:
            options['bounds'] = bounds

        return options

    # Determine the interval of data that we should request from Robinhood
    # given the required data span
    @staticmethod
    def interval_for_span(span):
        if span <= timedelta(days=1):
            return '5minute'
        elif span <= timedelta(days=7):
            return '10minute'
        elif span <= timedelta(days=365):
            return 'day'
        else:
            return 'week'

class StockChartData(RobinhoodChartData):
    def __init__(self, instrument, span=timedelta(days=1)):
        security_name = "{} ({})".format(
            instrument.simple_name or instrument.name,
            instrument.symbol
        )

        quote_result = RobinhoodChartData.call_async(Quote.get, instrument.id)

        historical_params = RobinhoodChartData.historical_params(instrument.list_date, span)
        historicals = Historicals.list(instrument.id, **historical_params)

        quote = quote_result.get()
        current_price = quote.last_extended_hours_trade_price or quote.last_trade_price

        initial_price = historicals.previous_close_price

        super().__init__(security_name, historicals, initial_price, current_price, span)

# Chart data for options, with appropriate overrides
class OptionChartData(RobinhoodChartData):

    def __init__(self, instrument, span=timedelta(days=1)):
        security_name = self.__get_security_name(instrument)

        quote_result = RobinhoodChartData.call_async(OptionQuote.get, instrument.id)

        historical_params = RobinhoodChartData.historical_params(instrument.issue_date, span)
        historicals = OptionHistoricals.list(instrument.id, **historical_params)

        quote = quote_result.get()
        current_price = quote.adjusted_mark_price

        initial_price = historicals.items[0].open_price

        super().__init__(security_name, historicals,
            initial_price, current_price, span)

    def __get_security_name(self, instrument):
        type = instrument.type[0].upper()
        expiration = instrument.expiration_date.strftime("%-x")
        price = round(instrument.strike_price, 1)
        symbol = instrument.chain_symbol

        return "{} {}{} {}".format(symbol, price, type, expiration)
