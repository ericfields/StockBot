from django.apps import AppConfig
from robinhood.models import Market

class QuotesConfig(AppConfig):
    name = 'quotes'

    def ready(self):
        import logging
        logger = logging.getLogger('stockbot')
        logger.info("Preloading market data")
        MARKET = 'XNYS'
        market = Market.get(MARKET)
        market_hours = market.hours()
