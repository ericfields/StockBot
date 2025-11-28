from indexes.models import Index, Asset
from robinhood.models import Stock, Option, Instrument
from robinhood.stock_handler import StockHandler
from robinhood.option_handler import OptionHandler
from exceptions import BadRequestException, NotFoundException
from helpers.pool import thread_pool
import logging

logger = logging.getLogger('stockbot')

"""Extracts instruments from multiple stocks/options/indexes and combines them into
batch queries to send to Robinhood API for instruments, quotes, and historical data.
"""
class Aggregator:
    stock_handler = StockHandler()
    option_handler = OptionHandler()

    def __init__(self, *items):
        self.instrument_map = {}
        self.quotes_map = {}
        self.historicals_map = {}

        self.instruments_loaded = False
        self.quotes_loaded = False
        self.historicals_loaded = False

        if items:
            self.load_instruments(*items)

    def load_instruments(self, *items):
        self.stock_identifiers = set()
        self.option_identifiers = set()

        self.set_identifiers_to_load(items)

        if self.stock_identifiers:
            stocks = self.stock_handler.find_instruments(*self.stock_identifiers)
            self.instrument_map.update(stocks)
        if self.option_identifiers:
            options = self.option_handler.find_instruments(*self.option_identifiers)
            self.instrument_map.update(options)

        self.instruments_loaded = True

        # Allow quotes/historicals to be reloaded when instruments are reloaded
        self.quotes_loaded = False
        self.historicals_loaded = False

        return self.instrument_map

    def get_instrument(self, item) -> Instrument:
        if not self.instruments_loaded:
            raise Exception("Instruments have not yet been loaded for this aggregator.")

        if type(item) in [Stock, Option]:
            return item

        if type(item) == Asset:
            identifier = item.instrument_url or Aggregator.get_identifier(item.identifier)
        elif type(item) == str:
            identifier = Aggregator.get_identifier(item)
        else:
            raise Exception("Cannot fetch instrument for type: {}".format(type(item)))

        if identifier not in self.instrument_map:
            raise Exception("Instrument has not been loaded for {}".format(identifier))

        return self.instrument_map[identifier]

    def instruments(self):
        if not self.instruments_loaded:
            raise Exception("Instruments have not yet been loaded for this aggregator.")

        return self.instrument_map

    def quotes_and_historicals(self, start_time, end_time):
        if not self.instruments_loaded:
            raise Exception("Instruments have not yet been loaded for this aggregator.")

        if not (self.quotes_loaded and self.historicals_loaded):
            historical_params = Instrument.historical_params(start_time, end_time)

            self.quotes_map, self.historicals_map = self.fetch_quotes_and_historicals(historical_params)

            self.quotes_loaded = True
            self.historicals_loaded = True

        return self.quotes_map, self.historicals_map

    def quotes(self):
        if not self.instruments_loaded:
            raise Exception("Instruments have not yet been loaded for this aggregator.")

        if not self.quotes_loaded:
            self.quotes_map = self.fetch_quotes_and_historicals()

            self.quotes_loaded = True

        return self.quotes_map

    def fetch_quotes_and_historicals(self, historical_params=None):
        stock_urls = set()
        option_urls = set()

        for identifier in self.instrument_map:
            # Use the URLs only
            if identifier.startswith('http'):
                url = identifier
                if type(self.instrument_map[url]) == Option:
                    option_urls.add(url)
                else:
                    stock_urls.add(url)
        quote_result_set = []
        historicals_result_set = []

        with thread_pool(4) as pool:
            if stock_urls:
                quote_result_set.append(pool.call(Stock.Quote.search, instruments=stock_urls))
                if historical_params:
                    historicals_result_set.append(pool.call(Stock.Historicals.search, instruments=stock_urls, **historical_params))
            if option_urls:
                quote_result_set.append(pool.call(Option.Quote.search, instruments=option_urls))
                if historical_params:
                    historicals_result_set.append(pool.call(Option.Historicals.search, instruments=option_urls, **historical_params))

        quotes_map = {}
        historicals_map = {}

        for quote_set in quote_result_set:
            quotes = quote_set.get()
            for q in quotes:
                instrument = self.instrument_map[q.instrument]
                quotes_map[instrument.url] = q
                quotes_map[instrument.identifier()] = q

        # Set extra identifiers as needed
        for identifier in self.instrument_map:
            instrument = self.instrument_map[identifier]
            if instrument.url in quotes_map:
                quotes_map[identifier] = quotes_map[instrument.url]

        if not historical_params:
            return quotes_map

        for historicals_set in historicals_result_set:
            historicals = historicals_set.get()
            for h in historicals:
                instrument = self.instrument_map[h.instrument]
                historicals_map[instrument.url] = h
                historicals_map[instrument.identifier()] = h

        for identifier in self.instrument_map:
            instrument = self.instrument_map[identifier]
            if instrument.url in historicals_map:
                historicals_map[identifier] = historicals_map[instrument.url]

        return quotes_map, historicals_map


    def get_identifier(item):
        if type(item) == str:
            identifier = item
        elif type(item) == Asset:
            identifier = item.identifier or item.instrument_url
        elif type(item) in [Stock, Option]:
            identifier = item.identifier()
        else:
            raise Exception("Cannot compute an asset identifier for type {}".format(type(item)))

        for handler in [Aggregator.stock_handler, Aggregator.option_handler]:
            if handler.valid_url(identifier):
                return identifier
            elif handler.valid_identifier(identifier):
                return handler.standard_identifier(identifier)

        raise Exception("Invalid identifier: {}".format(identifier))

    def set_identifiers_to_load(self, items):
        for item in items:
            if type(item) in [Stock, Option]:
                self.instrument_map[item.url] = item
                self.instrument_map[item.identifier()] = item
                continue

            if type(item) == Index:
                self.set_identifiers_to_load(item.assets())
                continue

            if type(item) == Asset:
                identifier = item.instrument_url
            elif type(item) == str:
                identifier = item
            else:
                raise Exception("Cannot determine identifier for {}".format(item.__class__.__name__))

            if self.stock_handler.valid_identifier(identifier):
                self.stock_identifiers.add(identifier)
            elif self.option_handler.valid_identifier(identifier):
                self.option_identifiers.add(identifier)
            else:
                raise BadRequestException("Invalid stock/option: '{}'".format(identifier))
