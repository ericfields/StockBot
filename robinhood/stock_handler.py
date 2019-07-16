from .instrument_handler import InstrumentHandler
from robinhood.models import Stock

class StockHandler(InstrumentHandler):
    TYPE = 'stock'
    FORMAT = '^[A-Z\.]{1,14}$'
    EXAMPLE = 'AMZN'

    def instrument_class(self):
        return Stock

    def get_search_params(self, identifier):
        return {
            'symbol': identifier
        }

    def standard_identifier(self, identifier):
        return identifier.upper()
