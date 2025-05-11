from django.apps import AppConfig
from robinhood.models import Market
from robinhood.api import ApiResource
from credentials import robinhood_credentials
import sys
import logging

logger = logging.getLogger('stockbot')

def get_credential(credential_key: str) -> str:
    return getattr(robinhood_credentials, credential_key, None)

class QuotesConfig(AppConfig):
    name = 'quotes'

    def ready(self):
        if 'test' in sys.argv:
            logger.info("Detected that we are in testing mode, enabling mocks for Robinhood API")
            ApiResource.enable_mock = True

        if {'runserver', 'uwsgi'}.intersection(set(sys.argv)):
            self.preload_market_info()

    def preload_market_info(self):
        logger.info("Preloading market data")
        MARKET = 'XNYS'
        market = Market.get(MARKET)
        market_hours = market.hours()
