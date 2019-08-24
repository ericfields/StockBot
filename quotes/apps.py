from django.apps import AppConfig
from robinhood.models import Market
from robinhood.api import ApiResource
import credentials
import sys

class QuotesConfig(AppConfig):
    name = 'quotes'

    def ready(self):
        self.load_auth_credentials()
        if {'test', 'runserver', 'uwsgi'}.intersection(set(sys.argv)):
            self.load_auth_credentials()
            #ApiResource.authenticate()
            if {'runserver', 'uwsgi'}.intersection(set(sys.argv)):
                self.preload_market_info()


    def load_auth_credentials(self):
        if credentials.robinhood_username and credentials.robinhood_password:
            ApiResource.username = credentials.robinhood_username
            ApiResource.password = credentials.robinhood_password
            ApiResource.oauth_client_id = credentials.robinhood_oauth_client_id
            ApiResource.device_token = credentials.robinhood_device_token

    def preload_market_info(self):
        import logging
        logger = logging.getLogger('stockbot')
        logger.info("Preloading market data")
        MARKET = 'XNYS'
        market = Market.get(MARKET)
        market_hours = market.hours()
