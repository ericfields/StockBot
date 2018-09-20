from .stock_quote_handler import StockQuoteHandler
from .option_quote_handler import OptionQuoteHandler
from uuid import UUID
from .utilities import *
from django.views.decorators.cache import cache_page
import re

QUOTE_HANDLERS = [StockQuoteHandler, OptionQuoteHandler]

def get_graph(request, identifiers, span = 'day'):
    span = str_to_duration(span)

    identifiers = identifiers.split(',')
    # Remove duplicates by converting to set (and back)
    identifiers = list(set(identifiers))

    instruments = find_instruments(identifiers)
    if len(instruments) == 1:
        chart_name = instruments[0].full_name()
    else:
        chart_name = ', '.join([i.short_name() for i in instruments])

    return chart_img(chart_name, span, instruments)

def get_mattermost_graph(request):
    body = request.POST.get('text', None)
    if not body:
        raise BadRequestException("No stocks/options specified")

    parts = body.split()
    identifiers = parts[0].upper().split(',')
    # Remove duplicates by converting to set (and back)
    identifiers = list(set(identifiers))

    if len(parts) > 1:
        span = parts[1]
        str_to_duration(span) # raise error if span is invalid
    else:
        span = 'day'

    instruments = find_instruments(identifiers)
    if len(instruments) == 1:
        chart_name = instruments[0].full_name()
    else:
        chart_name = ', '.join([i.short_name() for i in instruments])

    return mattermost_chart(request, chart_name, span, instruments)

@cache_page(60 * 15)
def get_graph_img(request, img_name):
    parts = img_name.split("_")
    if len(parts) < 3:
        raise BadRequestException("Invalid image: '{}'".format(img_name))

    identifiers = parts[0].split(',')
    span = str_to_duration(parts[-1])

    instruments = find_instruments(identifiers)
    if len(instruments) == 1:
        chart_name = instruments[0].full_name()
    else:
        chart_name = ', '.join([i.short_name() for i in instruments])

    return chart_img(chart_name, span, instruments)

def find_instruments(identifiers):
    instruments = []
    for identifier in identifiers:
        instrument = None
        for handler in QUOTE_HANDLERS:
            try:
                instrument = handler.get_instrument(UUID(identifier))
                if instrument:
                    break
            except ValueError:
                # Identifier is not a UUID. Search by its identifier string instead
                pass

            if re.match(handler.FORMAT, identifier.upper()):
                instrument = handler.search_for_instrument(identifier.upper())
                break

        if not instrument:
            # No valid handlers for this identifier format
            raise BadRequestException("Invalid identifier '{}'. Valid formats:\n\t{}".format(
                identifier, valid_format_example_str())
            )
        instruments.append(instrument)

    return instruments

def valid_format_example_str():
    return "\n\t".join(["{}: {}".format(h.TYPE, h.EXAMPLE) for h in QUOTE_HANDLERS])

def stock_info(request):
    symbol = request.POST.get('text', None)

    if not symbol:
        raise BadRequestException("No stock was specified")

    fundamentals = Fundamentals.get(symbol)
    response = fundamentals.description if fundamentals else 'Stock was not found'
    return mattermost_text(response)
