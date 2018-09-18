from django.http import HttpResponse, HttpResponseForbidden
from .exceptions import BadRequestException, ForbiddenException
from django.shortcuts import render
from robinhood.api import ApiBadRequestException, ApiForbiddenException
from robinhood.models import Instrument, OptionInstrument, OptionHistoricals, Fundamentals
from chart import Chart
from robinhood.chart_data import RobinhoodChartData
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from datetime import datetime, timedelta
from dateutil import parser as dateparser
import json
import re
from uuid import UUID

DURATION_FORMAT = '^([0-9]+)?\s*(day|week|month|year|all|d|w|m|y|a)s?$'
SYMBOL_FORMAT = '[A-Za-z0-9\.]{1,14}'
OPTION_PRICE_FORMAT = '[0-9]+(\.[0-9]+)?)([CcPp]'

# Create your views here.
def index(request):
    raise BadRequestException("Get outta here.")

@csrf_exempt
def info_GET(request, symbol):
    symbol = symbol.upper()
    fundamentals = Fundamentals.get(symbol)
    response = (fundamentals.description if fundamentals else "Stock was not found")
    return HttpResponse(response)

@csrf_exempt
def info_POST(request):
    symbol = request.POST.get('text', None)

    if not symbol:
        raise BadRequestException("No stock was specified")

    fundamentals = Fundamentals.get(symbol)
    response = fundamentals.description if fundamentals else 'Stock was not found'
    return mattermost_response(response)

@csrf_exempt
def graph_GET(request, identifier, span = 'day'):
    span = __str_to_duration(span)

    identifiers = identifier.split(',')

    instruments = [find_instrument(id) for id in identifiers]

    if len(instruments) == 1:
        name = __stock_name(instruments[0])
    else:
        name = ', '.join([i.symbol for i in instruments])

    chart_data = RobinhoodChartData(name, span, instruments)
    return chart_img(chart_data)

@csrf_exempt
def graph_POST(request):
    body = request.POST.get('text', None)
    if not body:
        raise BadRequestException("No stock was specified")

    parts = body.split()
    if not parts:
        raise BadRequestException("No arguments provided")

    symbols = parts[0].upper().split(',')

    if len(parts) > 1:
        span = parts[1]
        __str_to_duration(span) # raise error if span is invalid
    else:
        span = 'day'

    instruments = [find_instrument(symbol) for symbol in symbols]
    instrument_ids = ','.join(instrument.id for instrument in instruments)

    img_file_name = "{}_{}_{}.png".format(instrument_ids, datetime.now().strftime("%H%M"), span)

    image_url = request.build_absolute_uri(
        request.get_full_path() + "/image/" + img_file_name)

    return mattermost_graph(','.join(symbols), image_url)

@csrf_exempt
def option_graph_GET(request, identifier, price_str, expiration, span = 'day'):
    instrument = find_option_instrument(identifier, price_str, expiration)
    span = __str_to_duration(span)
    name = __option_name(instrument)

    try:
        chart_data = RobinhoodChartData(name, span, instrument)
    except ApiForbiddenException:
        raise ForbiddenException("Authentication is required for this endpoint, but credentials are expired or invalid.")

    return chart_img(chart_data)

@csrf_exempt
def option_graph_POST(request):
    body = request.POST.get('text', None)
    if not body:
        raise BadRequestException("No stock was specified")

    parts = body.split()
    if len(parts) < 3:
        raise BadRequestException("Not enough options parameters provided. Must provide: [symbol], [price/type], [expiration date]")

    symbol = parts[0].upper()
    price_str = parts[1]
    expiration = parts[2]

    instrument = find_option_instrument(symbol, price_str, expiration)

    if len(parts) > 3:
        span = parts[3]
    else:
        span = 'day'

    img_file_name = "{}_{}_{}.png".format(instrument.id, datetime.now().strftime("%H%M"), span)

    image_url = request.build_absolute_uri(
        request.get_full_path() + "/image/" + img_file_name)

    return mattermost_graph(symbol, image_url)

@csrf_exempt
@cache_page(60)
def graph_img(request, img_name):
    parts = img_name.split("_")
    if len(parts) < 3:
        raise BadRequestException("Invalid image: '{}'".format(img_name))

    identifiers = parts[0].split(',')
    span = parts[-1]

    span = __str_to_duration(span)
    instruments = [find_instrument(identifier) for identifier in identifiers]
    if len(identifiers) == 1:
        name = __stock_name(identifiers[0])
    else:
        name = ', '.join(instrument.symbol for instrument in instruments)
    print(name)

    chart_data = RobinhoodChartData(name, span, instruments)
    return chart_img(chart_data)

@csrf_exempt
@cache_page(60)
def option_graph_img(request, img_name):
    parts = img_name.split("_")
    if len(parts) < 3:
        raise BadRequestException("Invalid image: '{}'".format(img_name))

    identifier = parts[0]
    span = parts[-1]

    span = __str_to_duration(span)
    instrument = find_option_instrument(identifier)
    name = __option_name(instrument)

    chart_data = RobinhoodChartData(name, span, instrument)
    return chart_img(chart_data)

def chart_img(chart_data):
    chart = Chart(chart_data)
    chart_img_data = chart.get_img_data()
    return HttpResponse(chart_img_data, content_type="image/png")

def find_option_instrument(identifier, price_str = None, expiration = None):
    try:
        option_instrument = OptionInstrument.get(UUID(identifier))
    except ValueError:
        # Not a UUID, search using the option parameters instead
        if not(price_str and expiration):
            raise BadRequestException("Must provide price/type and expiration of option")
        instrument = find_instrument(identifier)

        match = re.match("^({})$".format(OPTION_PRICE_FORMAT), price_str)
        if not match:
            raise BadRequestException("Invalid strike price '{}'".format(price_str))

        price = float(match.groups()[0])
        if price % 0.5 != 0:
            raise BadRequestException("Invalid strike price '{}'. Prices must be in 50-cent increments.".format(price_str))

        type = 'call' if match.groups()[2].upper() == 'C' else 'put'

        try:
            expiration = dateparser.parse(expiration)
        except ValueError:
            raise BadRequestException("Invalid expiration date '{}'".format(expiration))

        option_instruments = OptionInstrument.search(chain_id=instrument.tradable_chain_id, strike_price=price)

        option_instrument = None
        for i in option_instruments:
            if i.strike_price == price and i.type == type and i.expiration_date == expiration:
                option_instrument = i
                break

        if not option_instrument:
            raise BadRequestException("No {} {} option available for {}".format(
                expiration.strftime("%x"), price_str, identifier))

    return option_instrument

def find_instrument(identifier):
    instrument = None
    try:
        instrument = Instrument.get(UUID(identifier))
    except ValueError:
        # Not a UUID, likely a stock symbol. Search for its instrument instead
        if not re.match(SYMBOL_FORMAT, identifier):
            raise BadRequestException("Invalid stock symbol: '{}'".format(identifier))

        try:
            instruments = Instrument.search(symbol=identifier)
        except ApiBadRequestException:
            raise BadRequestException("Stock not found: '{}'".format(identifier))

        if len(instruments) > 0:
            instrument = instruments[0]

        if not instrument:
            raise BadRequestException("Stock not found: '{}'".format(identifier))

    return instrument


def mattermost_graph(security_name, image_url):
    response = {
        "response_type": "in_channel",
        "attachments": [
            {
                "fallback": "{} Chart".format(security_name),
                "text": security_name,
                "image_url": image_url
            }
        ]
    }

    return HttpResponse(json.dumps(response), content_type="application/json")

def mattermost_text(text):
    return HttpResponse(json.dumps({"text": text}), content_type="application/json")

def __str_to_duration(duration_str):
    duration_str = duration_str.strip().lower()
    match = re.match(DURATION_FORMAT, duration_str)
    if not match:
        raise BadRequestException("Invalid span '{}'. Must be time unit and/or number, e.g. '3month'".format(duration_str))

    unit = match.groups()[1][0]
    if unit == 'd':
        duration = timedelta(days=1)
    elif unit == 'w':
        duration = timedelta(days=7)
    elif unit == 'm':
        duration = timedelta(days=31)
    elif unit == 'y':
        duration = timedelta(days=365)
    elif unit == 'a':
        # Max duration available is 5 years
        return timedelta(days=365*5)

    if match.groups()[0]:
        # Multiply by provided duration
        duration *= int(match.groups()[0])

    return duration

def __stock_name(instrument):
    return "{} ({})".format(
        instrument.simple_name or instrument.name,
        instrument.symbol
    )

def __option_name(instrument):
    type = instrument.type[0].upper()
    expiration = instrument.expiration_date.strftime("%-x")
    price = round(instrument.strike_price, 1)
    symbol = instrument.chain_symbol

    return "{} {}{} {}".format(symbol, price, type, expiration)
