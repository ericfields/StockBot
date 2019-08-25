from django.apps import AppConfig
from robinhood.models import Market
from robinhood.api import ApiResource
import credentials
import sys
import logging

logger = logging.getLogger('stockbot')

class QuotesConfig(AppConfig):
    name = 'quotes'

    def ready(self):
        if 'test' in sys.argv:
            logger.info("Detected that we are in testing mode, enabling mocks for Robinhood API")
            ApiResource.enable_mock = True

        if {'runserver', 'uwsgi'}.intersection(set(sys.argv)):
            self.load_auth_credentials()
            ApiResource.authenticate()
            self.preload_market_info()


    def load_auth_credentials(self):
        if credentials.robinhood_username and credentials.robinhood_password:
            ApiResource.username = credentials.robinhood_username
            ApiResource.password = credentials.robinhood_password
            ApiResource.oauth_client_id = credentials.robinhood_oauth_client_id
            ApiResource.device_token = credentials.robinhood_device_token

    def preload_market_info(self):
        logger.info("Preloading market data")
        MARKET = 'XNYS'
        market = Market.get(MARKET)
        market_hours = market.hours()
