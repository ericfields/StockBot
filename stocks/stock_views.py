from .exceptions import BadRequestException
from robinhood.api import ApiBadRequestException
from robinhood.models import Instrument, Fundamentals
from django.views.decorators.cache import cache_page
from .utilities import *
from uuid import UUID
import re

def stock_graph_GET(request, identifier, span = 'day'):
    span = str_to_duration(span)

    identifiers = identifier.split(',')
    # Remove duplicates by converting to set (and back)
    identifiers = list(set(identifiers))

    instruments = [find_stock_instrument(id) for id in identifiers]

    if len(instruments) == 1:
        name = chart_name_for_stock(instruments[0])
    else:
        name = ', '.join([i.symbol for i in instruments])

    return chart_img(name, span, instruments)

def stock_graph_POST(request):
    body = request.POST.get('text', None)
    if not body:
        raise BadRequestException("No stock was specified")

    parts = body.split()
    if not parts:
        raise BadRequestException("No arguments provided")

    symbols = parts[0].upper().split(',')
    # Remove duplicates by converting to set (and back)
    symbols = list(set(symbols))

    if len(parts) > 1:
        span = parts[1]
        str_to_duration(span) # raise error if span is invalid
    else:
        span = 'day'

    instruments = [find_stock_instrument(symbol) for symbol in symbols]

    chart_name = ', '.join(symbols)

    return mattermost_chart(request, chart_name, span, instruments)

def stock_info_POST(request):
    symbol = request.POST.get('text', None)

    if not symbol:
        raise BadRequestException("No stock was specified")

    fundamentals = Fundamentals.get(symbol)
    response = fundamentals.description if fundamentals else 'Stock was not found'
    return mattermost_text(response)

@cache_page(60 * 15)
def stock_graph_img(request, img_name):
    parts = img_name.split("_")
    if len(parts) < 3:
        raise BadRequestException("Invalid image: '{}'".format(img_name))

    identifiers = parts[0].split(',')
    span = parts[-1]

    span = str_to_duration(span)
    instruments = [find_stock_instrument(identifier) for identifier in identifiers]
    if len(instruments) == 1:
        name = chart_name_for_stock(instruments[0])
    else:
        name = ', '.join(instrument.symbol for instrument in instruments)

    return chart_img(name, span, instruments)

SYMBOL_FORMAT = '^[A-Z\.]{1,14}$'

def find_stock_instrument(identifier):
    instrument = None
    try:
        instrument = Instrument.get(UUID(identifier))
    except ValueError:
        # Not a UUID, likely a stock symbol. Search for its instrument instead
        identifier = identifier.upper()
        if not re.match(SYMBOL_FORMAT, identifier):
            raise BadRequestException("Invalid stock symbol: '{}'".format(identifier))

        try:
            instruments = Instrument.search(symbol=identifier)
        except ApiBadRequestException:
            raise BadRequestException("Invalid stock symbol: '{}'".format(identifier))

        if len(instruments) > 0:
            instrument = instruments[0]

        if not instrument:
            raise BadRequestException("Stock not found: '{}'".format(identifier))

    return instrument

def chart_name_for_stock(instrument):
    return "{} ({})".format(
        instrument.simple_name or instrument.name,
        instrument.symbol
    )

def stock_identifier(instrument):
    return instrument.symbol
