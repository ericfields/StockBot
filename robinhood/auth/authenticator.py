import requests
from datetime import datetime
from threading import Lock
from pathlib import Path

from credentials import robinhood_credentials

from .oauth_token import OAuthToken

class AuthProvider():
    """
    Class for use with Python requests, specifically when invoking request methods (request.get, request.post, request.requests).
    An instance of this class can be passed to the 'auth' argument of these methods.
    Sets authentication credentials on the request as needed.
    """
    def __call__(self, request: requests.Request) -> requests.Request:
        raise NotImplementedError("This AuthProvider has not been implemented")

class TokenAuthProvider(AuthProvider):
    oauth_token: OAuthToken

    # Non-Python User-Agent used so we don't get blocked by API gateways
    USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15'
    
    def __init__(self, oauth_token: OAuthToken):
        self.oauth_token = oauth_token

    def __call__(self, request: requests.Request):
        request.headers['Authorization'] = f"Bearer {self.oauth_token.access_token}"
        request.headers['User-Agent'] = self.USER_AGENT
        return request

class Authenticator():
    def auth_provider(self) -> AuthProvider:
        raise NotImplementedError("auth_provider must be implemented for this class")

class TokenAuthenticator(Authenticator):
    """
    Class for authenticating requests to Robinhood via OAuth, refreshing tokens as needed.
    This cannot perform username/password authentication, as Robinhood enforces two-factor authentication.
    However, a user derive the necessary details by logging into robinhood.com and retrieving them
    from the cookies and local storage of their web session.
    """

    AUTH_ENDPOINT = 'https://api.robinhood.com/oauth2/token/'
    DEFAULT_CLIENT_ID = "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS"

    # We will refresh the token periodically at a minimum of this time interval, regardless of time until expiration.
    DEFAULT_REFRESH_INTERVAL_SECS = 86400

    # Minimum time until token expiration before we must refresh.
    # Recommend three days, to account for StockBot inactivity over the weekend.
    DEFAULT_MIN_REFRESH_SECS_BEFORE_EXPIRATION = 86400 * 3 

    device_id: str
    client_id: str
    oauth_token: OAuthToken
    token_file: Path = None
    refresh_interval_secs: int
    min_refresh_secs_before_expiration: int

    __auth_provider: TokenAuthProvider

    refresh_lock = Lock()

    def __init__(self, device_id: str | Path, token: str | Path,
                 refresh_interval_secs: int = DEFAULT_REFRESH_INTERVAL_SECS,
                 min_refresh_secs_before_expiration: int = DEFAULT_MIN_REFRESH_SECS_BEFORE_EXPIRATION,
                 client_id: str = DEFAULT_CLIENT_ID,
                 refresh_on_initial_load: bool = True):
        """
        Parameters:
            device_id: Found in the cookie named 'device_id' in a robinhood.com web session. Can be specified as a string or a Path to a file containing the value.
                Specified in OAuth requests as 'device_token'.
            token: Found in the Local Storage under the key 'web:auth_state' in a robinhood.com web session. Can be specified as a string or a Path to a file containing the value. If Path specified, the file content be updated when token is refreshed.
                Can also be found in the session's Indexed Database, in the 'localforage' database,
                in table 'keyvaluepairs' in the row with key 'reduxPersist:auth', in a doubly JSON-escaped form.
                The Indexed DB value is the one Robinhood actually uses for authentication, though it should be the same
                as the localstorage value.
            client_id: The same for all Robinhood web sessions; changes rarely. (i.e. don't specify it if you don't need to).
                Buried in Robinhood's minified JavaScript, it can only be derived by inspecting the network request
                to create/refresh a token (api.robinhood.com/oauth2/token) and looking for 'client_id' in the JSON request body.
            refresh_interval_secs: Minimum time between token refreshes. Defaults to one day.
                The token will be automatically refreshed and stored within this authenticator object
                (and saved to the token_file as well if specified).
            min_refresh_secs_before_expiration: The minimum time prior to expiration refresh before which the token should be refreshed.
        """

        self.device_id = self.__read_param_value_or_file('device_id', device_id)

        if isinstance(token, Path):
            # Save the file path so we can update it as the token is refreshed.
            self.token_file = token
        
        token = self.__read_param_value_or_file('token', token)
        self.oauth_token = OAuthToken(token)
        self.__auth_provider = TokenAuthProvider(self.oauth_token)

        self.client_id = client_id
        self.refresh_interval_secs = refresh_interval_secs
        self.min_refresh_secs_before_expiration = min_refresh_secs_before_expiration

        if refresh_on_initial_load:
            self.refresh_token_if_needed()

    def auth_provider(self):
        self.refresh_token_if_needed()
        return self.__auth_provider

    def refresh_token_if_needed(self) -> bool:
        if not self.__refresh_reason():
            return False
        
        # Lock to ensure we only initiate one token refresh workflow at a time.
        # Each refresh invalidates the previous token; if concurrent refreshes occur,
        # some requests could be using tokens that are immediately invalidated.
        with self.refresh_lock:
            refresh_reason = self.__refresh_reason()
            if refresh_reason:
                print(f"Refreshing token ({refresh_reason})")
                return self.refresh_token()
    
        return False
            

    def refresh_token(self) -> bool:
        if (self.oauth_token.created_at and self.oauth_token.seconds_until_expiry() < 0):
            print("Warning: token appears to be expired. Authentication and refresh will likely fail.")
        
        refresh_token = self.oauth_token.refresh_token
        if not refresh_token:
            return False
        
        request_body = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'device_token': self.device_id,
            'scope': self.oauth_token.scope
        }

        response = requests.post(self.AUTH_ENDPOINT, json=request_body)

        if response.status_code != 200:
            print("Token refresh failed")
            print(self.response_details(response))
            return False
        
        token = response.content.decode()
        if not token:
            raise Exception("Response for token refresh did not contain new OAuth token")
        
        self.oauth_token = OAuthToken(token, created_at=datetime.now())
        self.__auth_provider = TokenAuthProvider(self.oauth_token)

        if self.token_file:
            self.oauth_token.write_to_file(self.token_file)

        return True
    
    @staticmethod
    def __read_param_value_or_file(param: str, arg: str | Path, required=True) -> str:
        if isinstance(arg, Path):
            try:
                value = arg.read_text().strip()
                if not value and required:
                    raise ValueError(f"{param} file is empty: {arg}")
            except Exception as e:
                raise ValueError(f"{param} could not be read from specified file {arg}", e)
        else:
            value = arg

        if not value and required:
            raise ValueError(f"{param} value cannot be None or empty")
        
        return value
        
    def __refresh_reason(self) -> str:
        if not self.oauth_token.created_at:
            return "No previous refresh or token refresh date unknown"
        
        seconds_until_expiry = self.oauth_token.seconds_until_expiry()
        if seconds_until_expiry < self.min_refresh_secs_before_expiration:
            return "Within minimum seconds before expiry"
        
        time_since_last_refresh = (datetime.now() - self.oauth_token.created_at).total_seconds()
        if time_since_last_refresh > self.refresh_interval_secs:
            return "Scheduled refresh interval"
        
        return None
    
    @staticmethod
    def response_details(response: requests.Response) -> str:
        msg = f"{response.status_code} {response.reason}"
        msg += f"\nURL: {response.url}"
        msg += f"\nResponse content: '{response.content.decode()}'"
        msg += f"\nResponse headers: {response.headers}"

        request_body = response.request.body
        if (request_body and type(request_body) == bytes):
            request_body = request_body.decode()

        msg += f"\nRequest content: '{request_body}'"
        msg += f"\nRequest headers: {response.request.headers}"

        return msg
    
AUTHENTICATOR = None
    
def load_authenticator_instance() -> Authenticator:
    """
    Loads a Robinhood TokenAuthenticator instance.
    Should be invoked once at startup time.
    Will return None if the Authenticator could not be loaded for whatever reason.
    """
    global AUTHENTICATOR
    if AUTHENTICATOR:
        return AUTHENTICATOR
    
    print("Initializing Authenticator...")
    AUTHENTICATOR = _load_authenticator()
    return AUTHENTICATOR


def _load_authenticator() -> Authenticator:
    device_id = robinhood_credentials.device_id
    oauth_token = robinhood_credentials.oauth_token
    client_id = robinhood_credentials.client_id

    try:
        return TokenAuthenticator(device_id, oauth_token, client_id=client_id)
    except ValueError as e:
        print("\nCould not initialize token authenticator", e)
        return None