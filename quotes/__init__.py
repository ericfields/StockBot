import config
from robinhood.api import ApiResource

if config.robinhood_username and config.robinhood_password:
    ApiResource.username = config.robinhood_username
    ApiResource.password = config.robinhood_password
    ApiResource.oauth_client_id = config.robinhood_oauth_client_id
    ApiResource.device_token = config.robinhood_device_token

    ApiResource.authenticate()
