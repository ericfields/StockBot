from django.apps import AppConfig
from robinhood.models import Market
from robinhood.api import ApiResource
from credentials import robinhood_credentials
import sys
import logging
import threading

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

        if threading.current_thread().name == 'MainThread':
            self.run_scheduled_token_refresh_if_needed(initial_run=True)

    def run_scheduled_token_refresh_if_needed(self, initial_run=False):
        authenticator = ApiResource.load_api_authenticator()
        if authenticator:
            interval = authenticator.refresh_interval_secs
            if initial_run:
                print(f"Scheduling token refresh every {interval} seconds")
            else:
                authenticator.refresh_token_if_needed()
        
            timer = threading.Timer(interval, self.run_scheduled_token_refresh_if_needed)
            timer.daemon = True
            timer.start()


    def preload_market_info(self):
        logger.info("Preloading market data")
        MARKET = 'XNYS'
        market = Market.get(MARKET)
        market.hours()
