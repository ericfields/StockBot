import credentials
from robinhood.api import ApiResource

if credentials.robinhood_username and credentials.robinhood_password:
    ApiResource.username = credentials.robinhood_username
    ApiResource.password = credentials.robinhood_password
    ApiResource.oauth_client_id = credentials.robinhood_oauth_client_id
    ApiResource.device_token = credentials.robinhood_device_token

    ApiResource.authenticate()
