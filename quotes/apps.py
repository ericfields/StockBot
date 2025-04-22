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
            self.load_auth_credentials()
            ApiResource.authenticate()
            self.preload_market_info()

    def load_auth_credentials(self):
        ApiResource.username = get_credential('robinhood_username')
        ApiResource.password = get_credential('robinhood_password')
        ApiResource.oauth_client_id = get_credential('robinhood_oauth_client_id')
        ApiResource.device_token = get_credential('robinhood_device_token')
        ApiResource.auth_access_token = get_credential('robinhood_access_token')
        ApiResource.auth_refresh_token = get_credential('robinhood_refresh_token')

    def preload_market_info(self):
        logger.info("Preloading market data")
        MARKET = 'XNYS'
        market = Market.get(MARKET)
        market_hours = market.hours()
