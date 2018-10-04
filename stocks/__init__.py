import config
from robinhood.api import ApiResource

if config.robinhood_username and config.robinhood_password and config.robinhood_client_id:
    ApiResource.username = config.robinhood_username
    ApiResource.password = config.robinhood_password
    ApiResource.client_id = config.robinhood_client_id

    ApiResource.authenticate()
