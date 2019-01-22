from portfolios.models import Portfolio, Asset
from robinhood.models import Stock, Option, Instrument
from quotes.stock_handler import StockHandler
from quotes.option_handler import OptionHandler
from multiprocessing.pool import ThreadPool
import re

"""Extracts instruments from multiple stocks/options/portfolios and combines them into
a single query to send to Robinhood API for quote/historical data.
"""

def quote_and_historicals_aggregate(start_time, end_time, *securities):
    instruments = extract_instruments(*securities)
    quote_call = async_call(quote_aggregate, *instruments)
    historicals_call = async_call(historicals_aggregate, start_time, end_time, *instruments)
    return quote_call.get(), historicals_call.get()

def quote_aggregate(*securities):
    instrument_list = extract_instruments(*securities)
    instruments = instrument_url_map(*instrument_list)
    stock_urls, option_urls = get_instrument_urls(instruments)

    stock_results = option_results = None
    if stock_urls:
        stock_results = async_call(Stock.Quote.search, instruments=stock_urls)
    if option_urls:
        option_results = async_call(Option.Quote.search, instruments=option_urls)

    quotes = []
    if stock_results:
        quotes += stock_results.get()
    if option_results:
        quotes += option_results.get()

    quote_map = {}
    for quote in quotes:
        if quote.instrument in instruments:
            instrument = instruments[quote.instrument]
        quote_map[instrument.id] = quote

    return quote_map

def historicals_aggregate(start_date, end_date, *securities):
    instrument_list = extract_instruments(*securities)
    instruments = instrument_url_map(*instrument_list)
    stock_urls, option_urls = get_instrument_urls(instruments)

    historical_params = Instrument.historical_params(start_date, end_date)

    stock_results = option_results = None
    if stock_urls:
        stock_results = async_call(Stock.Historicals.search, instruments=stock_urls, **historical_params)
    if option_urls:
        option_results = async_call(Option.Historicals.search, instruments=option_urls, **historical_params)

    historicals = []
    if stock_results:
        historicals += stock_results.get()
    if option_results:
        historicals += option_results.get()

    historicals_map = {}
    for historical in historicals:
        if historical.instrument in instruments:
            instrument = instruments[historical.instrument]
        historicals_map[instrument.id] = historical

    return historicals_map

def get_instrument_urls(instruments):
    stock_urls, option_urls = set(), set()
    for instrument_url, instrument in instruments.items():
        if type(instrument) == Stock:
            stock_urls.add(instrument_url)
        elif type(instrument) == Option:
            option_urls.add(instrument_url)

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

def instrument_url_map(*instruments):
    return {i.instrument_url():i for i in instruments}

def instrument_from_asset(asset):
    if asset.type == Asset.STOCK:
        instrument = Stock(id=asset.instrument_id)
    elif asset.type == Asset.OPTION:
        instrument = Option(id=asset.instrument_id)
    else:
        raise Exception("Invalid asset type: {}".format(asset.type))
    return instrument

def async_call(method, *args, **kwargs):
    pool = ThreadPool(processes=1)
    return pool.apply_async(method, tuple(args), kwargs)
