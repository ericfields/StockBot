from .handler import Handler
from exceptions import BadRequestException
from robinhood.models import Stock
from django.views.decorators.cache import cache_page
import re

class StockHandler(Handler):

    TYPE = 'stock'
    FORMAT = '^[A-Z\.]{1,14}$'
    EXAMPLE = 'AMZN'

    def get_instrument(instrument_uuid):
        return Stock.get(instrument_uuid)

    def search_for_instrument(identifier):
        instruments = Stock.search(symbol=identifier)

        if len(instruments) > 0:
            # Haven't yet seen more than one instrument returned from a symbol query.
            # Just in case though, return the first instrument (and hope it's the one we want)
            return instruments[0]
        else:
            raise BadRequestException("Stock not found: '{}'".format(identifier))

    def valid_identifier(identifier):
        return re.match(StockHandler.FORMAT, identifier)
