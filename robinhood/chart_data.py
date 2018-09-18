import pandas as pd
from chart_data import ChartData
from multiprocessing.pool import ThreadPool
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from robinhood.models import Instrument, Quote, Historicals, OptionInstrument, OptionQuote, OptionHistoricals, Market

# Name of market to use in Robinhood
MARKET = 'XNYS'

class RobinhoodChartData(ChartData):

    def __init__(self, name, span, instruments):
        current_price = 0
        initial_price = 0

        stock_instrument_urls = []
        option_instrument_urls = []

        market = Market.get(MARKET)
        market_timezone = market.timezone
        market_hours = self.__get_market_hours(market)

        start_date = self.__get_start_date(span, market_hours)

        instrument_weights = {}
        if type(instruments) == dict:
            # Hash with weighted values for each instrument
            for i in instruments:
                instrument_weights[i.url] = instruments[i]
        elif type(instruments) == list:
            # List of instruments with no weights assigned
            # Give everything an equal weight of 1
            for i in instruments:
                instrument_weights[i.url] = 1
        else:
            # A single instrument
            instruments = [instruments]
            instrument_weights[instruments[0].url] = 1

        for i in instruments:
            if type(i) is OptionInstrument:
                option_instrument_urls.append(i.url)
            else:
                stock_instrument_urls.append(i.url)

        historical_params = self.__class__.historical_params(start_date, span)
        historicals_list = []

        if stock_instrument_urls:
            stock_quotes = Quote.search(instruments=stock_instrument_urls)
            for stock_quote in stock_quotes:
                weight = instrument_weights[stock_quote.instrument]
                current_price += (stock_quote.last_extended_hours_trade_price or stock_quote.last_trade_price) * weight
            historical_params['instruments'] = stock_instrument_urls
            historicals_list += Historicals.search(**historical_params)

        if option_instrument_urls:
            option_quotes = OptionQuote.search(instruments=option_instrument_urls)
            for option_quote in option_quotes:
                weight = instrument_weights[option_quote.instrument]
                current_price += option_quote.adjusted_mark_price * weight
            historical_params['instruments'] = option_instrument_urls
            historicals_list += OptionHistoricals.search(**historical_params)

        time_price_map = {}

        for historicals in historicals_list:
            weight = instrument_weights[historicals.instrument]
            initial_price_set = False

            if type(historicals) is Historicals and historicals.previous_close_price:
                initial_price += historicals.previous_close_price * weight
                initial_price_set = True

            for historical in historicals.items:
                # Exclude data before our requested start date
                if historical.begins_at < start_date:
                    continue

                if not initial_price_set:
                    initial_price += historical.close_price * weight
                    print(initial_price)
                    initial_price_set = True

                if historical.begins_at not in time_price_map:
                    time_price_map[historical.begins_at] = 0
                time_price_map[historical.begins_at] += historical.close_price * weight

        super().__init__(name, market_timezone, market_hours, time_price_map, initial_price, current_price, span)

    def __get_start_date(self, span, market_hours):
        start_date = datetime.now() - span
        # Get previous trading day's market hours if it is a weekend/holiday
        if start_date > market_hours.extended_opens_at:
            start_date = market_hours.extended_opens_at
        return start_date

    def __get_market_hours(self, market):
        market_hours = Market.hours(MARKET, datetime.now())
        if not market_hours.is_open or datetime.now() < market_hours.extended_opens_at:
            # Get market hours for the previous open day
            date = market_hours.previous_open_hours.split('/')[-2]
            market_hours = Market.hours(MARKET, date)
        return market_hours

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
