import config
from robinhood.models import ApiResource

ApiResource.username = config.robinhood_username
ApiResource.password = config.robinhood_password
ApiResource.client_id = config.robinhood_client_id
