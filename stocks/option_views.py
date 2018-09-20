from .exceptions import BadRequestException, ForbiddenException, ConfigurationException
from robinhood.api import ApiResource, ApiForbiddenException
from robinhood.models import OptionInstrument
from django.views.decorators.cache import cache_page
from .utilities import *
from stocks.stock_views import find_stock_instrument
from dateutil import parser as dateparser
from uuid import UUID
import re

def option_graph_GET(request, identifier, span = 'day'):
    span = str_to_duration(span)

    identifiers = identifier.split(',')
    # Remove duplicates by converting to set (and back)
    identifiers = list(set(identifiers))

    instruments = [find_option_instrument(i) for i in identifiers]

    if len(instruments) == 1:
        chart_name = chart_name_for_option(instruments[0])
    else:
        chart_name = ', '.join([option_simple_name(i) for i in instruments])

    try:
        return chart_img(chart_name, span, instruments)
    except ApiForbiddenException:
        raise ForbiddenException("Authentication is required for this endpoint, but credentials are expired or invalid.")

def option_graph_POST(request):
    if not ApiResource.api_token:
        raise ConfigurationException("Can't get a graph of options. Options history is authenticated, but no Robinhood credentials are configured for this server.")

    body = request.POST.get('text', None)
    if not body:
        raise BadRequestException("No parameters provided")

    parts = body.split()
    identifiers = parts[0].split(',')

    instruments = [find_option_instrument(i) for i in identifiers]

    if len(parts) > 1:
        span = parts[1]
        str_to_duration(span) # Verify that the span is valid
    else:
        span = 'day'

    chart_name = ', '.join([option_simple_name(i) for i in instruments])

    return mattermost_chart(request, chart_name, span, instruments)

@cache_page(60)
def option_graph_img(request, img_name):
    parts = img_name.split("_")
    if len(parts) < 3:
        raise BadRequestException("Invalid image: '{}'".format(img_name))

    identifiers = parts[0].split(',')
    span = parts[-1]

    span = str_to_duration(span)
    instruments = [find_option_instrument(i) for i in identifiers]
    if len(instruments) == 1:
        chart_name = chart_name_for_option(instruments[0])
    else:
        chart_name = ', '.join([option_simple_name(i) for i in instruments])
    return chart_img(chart_name, span, instruments)

OPTION_FORMAT = '^([A-Z\.]+)([0-9]+(\.50?)?)([CP])@?([0-9\/\-]+)?$'

def find_option_instrument(identifier):
    try:
        return OptionInstrument.get(UUID(identifier))
    except ValueError:
        # Value is not a valid UUID, likely an option identifier string
        pass

    option_instrument = None

    identifier = identifier.upper()
    symbol, price, type, expiration = parse_option(identifier)

    stock_instrument = find_stock_instrument(symbol)

    option_instruments = OptionInstrument.search(
        chain_id=stock_instrument.tradable_chain_id,
        strike_price=price,
        type=type,
        state='active'
    )
    # Sort options in order of expiration date
    if option_instruments:
        option_instruments.sort(key=lambda o: o.expiration_date)

        if expiration:
            try:
                option_instrument = next(i for i in option_instruments if i.expiration_date == expiration)
            except StopIteration:
                pass
        else:
            # Get the option expiring earliest, i.e. an "FD"
            option_instrument = option_instruments[0]

    if not option_instrument:
        message = "No tradeable {} ${} {} option".format(symbol, round(price, 1), type)
        if expiration:
            message += " expiring {}".format(expiration.strftime("%-x"))
        raise BadRequestException(message)

    return option_instrument

def parse_option(option_str):
    match = re.match(OPTION_FORMAT, option_str)
    if not match:
        raise BadRequestException("Invalid format for option: '{}'. Valid example: MU50.5C@12/21".format(option_str))

    parts = match.groups()

    symbol = parts[0]
    price = float(parts[1])
    if parts[3] == 'C':
        type = 'call'
    else:
        type = 'put'
    expiration = parts[4]

    if expiration:
        # Parse expiration date string
        expiration = parse_date(expiration)

    return symbol, price, type, expiration

def parse_date(date_str):
    # Convert from simple 4-digit and 8-digit formats
    if re.match('^[0-9]{4}$', date_str):
        date_str = '/'.join([date_str[0:2], date_str[2:4]])
    elif re.match('^[0-9]{8}$', date_str):
        date_str = '/'.join([date_str[0:2], date_str[2:4], date_str[4:8]])

    try:
        return dateparser.parse(date_str)
    except ValueError:
        raise BadRequestException("Invalid date: '{}'".format(date_str))

def option_identifier(instrument):
    type = instrument.type[0].upper()
    expiration = instrument.expiration_date.strftime("%D")
    price = instrument.strike_price
    if price % 1 > 0:
        price = round(price, 1)
    else:
        price = round(price)
    symbol = instrument.chain_symbol
    return "{}{}{}@{}".format(symbol, price, type, expiration)

def option_simple_name(instrument):
    type = instrument.type[0].upper()
    expiration = instrument.expiration_date.strftime("%-m/%-d")
    price = instrument.strike_price
    if price % 1 > 0:
        price = round(price, 1)
    else:
        price = round(price)
    symbol = instrument.chain_symbol

    return "{} ${}{} {}".format(symbol, price, type, expiration)

def chart_name_for_option(instrument):
    symbol = instrument.chain_symbol
    price = instrument.strike_price
    if price % 1 > 0:
        price = round(price, 1)
    else:
        price = round(price)
    type = instrument.type.capitalize()
    expiration = instrument.expiration_date.strftime("%-m/%-d")

    return "{} ${} {} {}".format(symbol, price, type, expiration)
