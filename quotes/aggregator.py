from portfolios.models import Portfolio, Asset
from robinhood.models import Stock, Option, Instrument
from quotes.stock_handler import StockHandler
from quotes.option_handler import OptionHandler
from multiprocessing.pool import ThreadPool
import re

"""Extracts instruments from multiple stocks/options/portfolios and combines them into
a single query to send to Robinhood API for quote/historical data.
"""

pool = ThreadPool(processes=10)

def quote_and_historicals_aggregate(start_time, end_time, *securities):
    instruments = extract_instruments(*securities)

    historical_params = Instrument.historical_params(start_time, end_time)

    quotes, historicals = fetch_data(instruments, historical_params)

    instrument_map = {i.instrument_url():i for i in instruments}

    quote_map = {}
    historicals_map = {}
    for q in quotes:
        if q.instrument in instrument_map:
            instrument = instrument_map[q.instrument]
            quote_map[instrument.id] = q
    for h in historicals:
        if h.instrument in instrument_map:
            instrument = instrument_map[h.instrument]
            historicals_map[instrument.id] = h

    return quote_map, historicals_map

def quote_aggregate(*securities):
    instruments = extract_instruments(*securities)

    quotes = fetch_data(instruments)

    instrument_map = {i.instrument_url():i for i in instruments}

    quote_map = {}
    for q in quotes:
        if q.instrument in instrument_map:
            instrument = instrument_map[q.instrument]
        quote_map[instrument.id] = q

    return quote_map

def fetch_data(instruments, historical_params=None):
    stock_urls, option_urls = get_instrument_urls(instruments)

    quote_result_set = []
    historicals_result_set = []
    if stock_urls:
        quote_result_set.append(async_call(Stock.Quote.search, instruments=stock_urls))
        if historical_params:
            historicals_result_set.append(async_call(Stock.Historicals.search, instruments=stock_urls, **historical_params))
    if option_urls:
        quote_result_set.append(async_call(Option.Quote.search, instruments=option_urls))
        if historical_params:
            historicals_result_set.append(async_call(Option.Historicals.search, instruments=option_urls, **historical_params))

    quotes = [q for quotes in quote_result_set for q in quotes.get()]
    if not historical_params:
        return quotes

    historicals = [h for historicals in historicals_result_set for h in historicals.get()]

    return quotes, historicals

def get_instrument_urls(instruments):
    stock_urls, option_urls = set(), set()
    for instrument in instruments:
        if type(instrument) == Stock:
            stock_urls.add(instrument.instrument_url())
        elif type(instrument) == Option:
            option_urls.add(instrument.instrument_url())

    return list(stock_urls), list(option_urls)

def extract_instruments(*securities):
    instruments = []
    for security in securities:
        instrument = None

        security_type = type(security)
        if security_type == Portfolio:
            for asset in security.assets():
                instruments.append(instrument_from_asset(asset))
        elif security_type == Asset:
            instruments.append(instrument_from_asset(security))
        elif security_type == Stock or security_type == Option:
            instruments.append(security)
        elif security_type == str:
            if StockHandler.valid_identifier(security):
                handler = StockHandler
            elif OptionHandler.valid_identifier(security):
                handler = OptionHandler
            else:
                raise Exception("String is not a valid stock/option: '{}'".format(security))
            instruments.append(handler.search_for_instrument(security))
        else:
            raise Exception("Invalid security type: {}".format(security_type))

    return instruments

def instrument_from_asset(asset):
    if asset.type == Asset.STOCK:
        instrument = Stock(id=asset.instrument_id)
    elif asset.type == Asset.OPTION:
        instrument = Option(id=asset.instrument_id)
    else:
        raise Exception("Invalid asset type: {}".format(asset.type))
    return instrument

def async_call(method, *args, **kwargs):
    return pool.apply_async(method, tuple(args), kwargs)
