from .quote_handler import QuoteHandler
from .exceptions import BadRequestException
from robinhood.models import Instrument
from django.views.decorators.cache import cache_page

class StockQuoteHandler(QuoteHandler):

    TYPE = 'stock'
    FORMAT = '^[A-Z\.]{1,14}$'
    EXAMPLE = 'AMZN'

    def get_instrument(instrument_uuid):
        return Instrument.get(instrument_uuid)

    def search_for_instrument(identifier):
        instruments = Instrument.search(symbol=identifier)

        if len(instruments) > 0:
            # Haven't yet seen more than one instrument returned from a symbol query.
            # Just in case though, return the first instrument (and hope it's the one we want)
            return instruments[0]
        else:
            raise BadRequestException("Stock not found: '{}'".format(identifier))

    def instrument_full_name(instrument):
        return "{} ({})".format(
            instrument.simple_name or instrument.name,
            instrument.symbol
        )

    def instrument_simple_name(instrument):
        return instrument.symbol

    def instrument_identifier(instrument):
        return instrument.symbol
