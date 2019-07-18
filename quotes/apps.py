from django.apps import AppConfig
from robinhood.models import Market
import sys

class QuotesConfig(AppConfig):
    name = 'quotes'

    def ready(self):
        if not 'test' in sys.argv: # Don't do this if just running unit tests
            import logging
            logger = logging.getLogger('stockbot')
            logger.info("Preloading market data")
            MARKET = 'XNYS'
            market = Market.get(MARKET)
            market_hours = market.hours()
