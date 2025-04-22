import requests
from datetime import date, datetime, timedelta
from dateutil import parser as dateparser
import pytz
import re
import json
from threading import RLock
from time import sleep
import hashlib
import logging
from time import time
from helpers.cache import Cache
import inspect
from exceptions import NotFoundException
from requests import Response

ROBINHOOD_ENDPOINT = 'https://api.robinhood.com'

AUTH_INFO = {
    'url': ROBINHOOD_ENDPOINT + "/oauth2/token/",
    'headers': {
        'Content-Type': 'application/json',
        'X-Robinhood-API-Version': '1.431.4'
    }
}

logger = logging.getLogger('stockbot')

AUTH_DURATION = timedelta(days=1)

class ApiModel():
    attributes = {}
    data = {}

    username = None
    password = None
    device_token = None
    oauth_client_id = None

    permanent_auth_failure = None

    # Flag indicating a type reference to the current class
    class CurrentClass():
        pass


    def __init__(self, **data):
        self.data = data
        self.__assign_attributes(data)

    def __assign_attributes(self, data):
        for attr in self.attributes:
            if attr in data:
                val = self.__typed_attribute(attr, data[attr])
                setattr(self, attr, val)
            elif attr not in locals():
                # Initialize all missing attributes as None
                setattr(self, attr, None)
        # Load variables for list items if they exist
        if 'items' in data:
            self.items = data['items']
        else:
            try:
                item_class = self.__class__.Item
                list_key = item_class.list_key
                if list_key in data:
                    self.items = [item_class(**item) for item in data[list_key]]
            except AttributeError:
                # Not a listable item class
                pass

    def raw_data(self):
        data = {}
        for attr in self.attributes:
            val = getattr(self, attr)
            if val is not None:
                attr_type = self.attributes[attr]
                if val and type(attr_type) == type and issubclass(attr_type, ApiModel):
                    if inspect.isclass(val):
                        val = val.raw_data()
                    else:
                        val = val().raw_data()
                elif attr_type in [int, float, date, pytz.timezone]:
                    val = str(val)
            data[attr] = val

        # Set items list if present in class
        try:
            item_class = self.__class__.Item
            list_key = item_class.list_key
            try:
                data[list_key] = [i.raw_data() for i in self.items]
            except AttributeError as e:
                raise Exception(e)
        except AttributeError:
            # Not a listable item class
            pass
        return data

    def __typed_attribute(self, attr, val):
        if val == None:
            return val
        attr_type = self.attributes[attr]
        if attr_type == None:
            return val
        elif attr_type == date:
            if type(val) is str:
                val = dateparser.parse(val).date()
            elif type(val) is datetime:
                val = val.date()
            elif type(val) is not date:
                raise ValueError(f"Cannot extract date from value of type '{type(val)}'")
            return val
        elif attr_type == datetime:
            if type(val) in [int, float]:
                val = datetime.fromtimestamp(val)
            elif type(val) is str:
                val = dateparser.parse(val).astimezone(pytz.utc).replace(tzinfo=None)
            elif type(val) is not datetime:
                raise ValueError(f"Cannot extract datetime from value of type '{type(val)}'")
            return val
        elif attr_type == bool:
            return val in [True, 'true', 'True', 't', 1]
        elif type(attr_type) == type and issubclass(attr_type, ApiModel) or attr_type == self.__class__.CurrentClass:
            # Value is a URL pointing to another resource.
            # Create a method for retrieving the object
            if attr_type == self.__class__.CurrentClass:
                # CurrentClass is just a flag; the actual class is the current calling class
                attr_type = self.__class__

            def resource_function():
                return attr_type(**attr_type.request(val))
            return resource_function
        else:
            try:
                return attr_type(val)
            except TypeError:
                raise Exception(f"Could not cast value as {attr_type}: {val}")

class ApiCallException(Exception):
    code = None
    body = None

    def __init__(self, code, body):
        self.code = code
        self.body = body
        message = "{}: {}".format(code, body)
        super().__init__(message)

class RobinhoodCredentialsException(Exception):
    pass

class ApiInternalErrorException(ApiCallException):
    pass

class ApiForbiddenException(ApiCallException):
    def __init__(self, message = None):
        if not message:
            message = "Robinhood authentication credentials expired or not provided"
        super().__init__(403, message)

class ApiBadRequestException(ApiCallException):
    def __init__(self, message):
        super().__init__(400, message)

class ApiUnauthorizedException(ApiCallException):
    def __init__(self, message):
        super().__init__(401, message)

class ApiThrottledException(ApiCallException):
    def __init__(self, message):
        super().__init__(429, message)


class ApiResource(ApiModel):
    api_endpoint = ROBINHOOD_ENDPOINT
    endpoint_path = ''

    authenticated = False

    auth_access_token = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIiLCJ0eXAiOiJKV1QifQ.eyJkY3QiOjE2NzA2MTkxMzEsImRldmljZV9oYXNoIjoiYjRmMWVlNzA5OWM2YjBmNTNiM2FhNTZlZjEyNTY1NzciLCJleHAiOjE3NDU5NDYxMDQsImxldmVsMl9hY2Nlc3MiOmZhbHNlLCJtZXRhIjp7Im9pZCI6ImM4MlNIMFdaT3NhYk9YR1Ayc3hxY2ozNEZ4a3ZmbldSWkJLbEJqRlMiLCJvbiI6IlJvYmluaG9vZCJ9LCJvcHRpb25zIjp0cnVlLCJwb3MiOiJwIiwic2NvcGUiOiJpbnRlcm5hbCIsInNlcnZpY2VfcmVjb3JkcyI6W3siaGFsdGVkIjpmYWxzZSwic2VydmljZSI6Im51bW11c191cyIsInNoYXJkX2lkIjoxLCJzdGF0ZSI6ImF2YWlsYWJsZSJ9LHsiaGFsdGVkIjpmYWxzZSwic2VydmljZSI6ImJyb2tlYmFja191cyIsInNoYXJkX2lkIjo0LCJzdGF0ZSI6ImF2YWlsYWJsZSJ9XSwic2xnIjoxLCJzbHMiOiJ4bkE0OExhM01MSzRISWRlaFNlS0FpT2IyRXVJaEozclpuRVdNMlFJTjJ6UzkwcnRFUXd2RFNYb3BzMFV5SlMveVp1dGRWWFdpdW1KMnR6VWh2SmpCUT09Iiwic3JtIjp7ImIiOnsiaGwiOmZhbHNlLCJyIjoidXMiLCJzaWQiOjR9LCJuIjp7ImhsIjpmYWxzZSwiciI6InVzIiwic2lkIjoxfX0sInRva2VuIjoic3c2aTh3Vkc1ZzdSRThMWldhSXVFaDllNVBERTZsIiwidXNlcl9pZCI6IjhiYThlZmI4LWE1YjEtNGU4NS1hYTM5LWNmNzA4NDllNzQwOSIsInVzZXJfb3JpZ2luIjoiVVMifQ.99H4ZKhgJP0Zm8kBzQ1GMnfojrhyr1Yimyfd013GZgOmpx-Lecv9uraTUdUHwEfltfU2kx3v1mj8F0oIx6DzkA"
    auth_refresh_token = "PVMA29kLk7G385zjdn7qic7AdgbFhS"
    auth_expiration = None
    auth_lock = RLock()

    enable_cache = True
    cache_timeout = None

    enable_mock = False
    mock_results = {}

    @classmethod
    def search(cls, **params):
        results = []
        data = cls.request(cls.resource_url(), **params)
        while data and 'results' in data:
            results.extend([cls(**result) for result in data['results'] if result])
            if 'next' in data and data['next']:
                # Keep requesting until all data has been returned
                next_url = re.sub('\\/', '/', data['next'])
                data = cls.request(next_url)
            else:
                break
        return results

    @classmethod
    def get(cls, resource_id, **params):
        if re.match("^https:\\/\\/", str(resource_id)):
            resource_url = resource_id
        else:
            resource_url = cls.resource_url(resource_id)
        data = cls.request(resource_url, **params)
        if data:
            return cls(**data)
        else:
            return None


    @staticmethod
    def authenticate(force_refresh=False, force_reauth=False):
        if ApiResource.enable_mock:
            # We are about to make an authentication request, which
            # should not occur when we are in mock mode
            raise Exception("Attempting to make authentication request when mocking enabled")

        missing_credentials = []
        if not ApiResource.device_token:
            missing_credentials.append('robinhood_device_token not set')
        if not ApiResource.oauth_client_id:
            missing_credentials.append('robinhood_oauth_client_id not set')

        if not (ApiResource.auth_access_token or ApiResource.auth_refresh_token) and not (ApiResource.username and ApiResource.password):
            missing_credentials.append('Must specify either robinhood_username/robinhood_password or robinhood_access_token/robinhood_refresh_token')
        if missing_credentials:
            missing_credentials_str = "; ".join(missing_credentials)
            raise RobinhoodCredentialsException(f"One or more required Robinhood credentials are not present ({"; ".join(missing_credentials)})")

        # If authentication has already failed, do not try again
        if ApiResource.permanent_auth_failure:
            raise ApiResource.permanent_auth_failure

        # Use locking to make sure that we are not trying to authenticate
        # from several threads at once
        # Release the lock first if we happen to own it
        ApiResource.auth_lock.acquire()
        try:
            # We should check the cache's value before our local instance,
            # as another process may have already reauthenticated and set the value
            access_token = Cache.get('auth_access_token') or ApiResource.auth_access_token
            auth_expiration = Cache.get('auth_expiration') or ApiResource.auth_expiration

            if not force_refresh and not force_reauth:
                if access_token and (not auth_expiration or datetime.now() < auth_expiration):
                    return access_token

            refresh_token = Cache.get('auth_refresh_token') or ApiResource.auth_refresh_token

            attempts = 3

            while True:
                attempts -= 1


                auth_url: str = AUTH_INFO['url']
                auth_headers: map = AUTH_INFO['headers']

                if refresh_token and not force_reauth:
                    print("Performing token refresh workflow...")
                    data = {
                        'grant_type': 'refresh_token',
                        'refresh_token': refresh_token,
                        'client_id': ApiResource.oauth_client_id,
                        'device_token': ApiResource.device_token,
                        'scope': 'internal'
                    }
                elif ApiResource.username and ApiResource.password:
                    data = {
                        'grant_type': 'password',
                        'expires_in': AUTH_DURATION.total_seconds(),
                        'username': ApiResource.username,
                        'password': ApiResource.password,
                        'client_id': ApiResource.oauth_client_id,
                        'device_token': ApiResource.device_token,
                        'scope': 'internal'
                    }
                else:
                    raise Exception("Authentication failed, and no remaining valid auth credentials. Cannot authenticate with Robinhood.")

                try:
                    response = requests.post(auth_url, headers=auth_headers, json=data)
                except requests.exceptions.ConnectionError as e:
                    # Occasional error, retry if possible
                    if attempts > 0:
                        sleep(1)
                        continue

                    raise e
                
                if response.status_code != 200:
                    print_response(response)

                if response.status_code == 200:
                    data = response.json()

                    access_token = data['access_token']
                    refresh_token = data['refresh_token']

                    auth_refresh_duration = AUTH_DURATION / 2
                    auth_expiration = datetime.now() + auth_refresh_duration

                    # Set the access token to expire early to allow the refresh token to be utilized
                    Cache.set('auth_access_token', access_token, auth_refresh_duration.total_seconds())
                    Cache.set('auth_refresh_token', refresh_token, AUTH_DURATION.total_seconds())
                    Cache.set('auth_expiration', auth_expiration)

                    # Define in local memory (we may not have a cache available to us)
                    ApiResource.auth_expiration = auth_expiration
                    ApiResource.auth_access_token = access_token
                    ApiResource.auth_refresh_token = refresh_token

                    return access_token

                if response.status_code >= 500:
                    if attempts > 0:
                        sleep(1)
                        continue

                    raise ApiInternalErrorException(response.status_code, response.text)

                if response.status_code == 429:
                    raise ApiThrottledException(response.text)

                # If we reach this point we've likely received an authentication error
                # Remove cached credentials and force reauthentication
                force_refresh = True
                Cache.delete('auth_refresh_token')
                Cache.delete('auth_expiration')
                ApiResource.auth_access_token = None
                ApiResource.auth_expiration = None

                if response.status_code == 401:
                    try:
                        response_data = response.json()
                        if 'error' in response_data and response_data['error'] == 'invalid_grant':
                            print_response(response)
                            print("Refresh token is invalid")
                        
                            # Refresh token is no longer valid
                            # Remove it and re-attempt authentication with username/password
                            refresh_token = None


                            return ApiResource.authenticate(force_reauth=True)
                    except ValueError:
                        # Response is not valid JSON, let remaining error logic handle it
                        pass

                # Error codes other than these are considered to be permanent errors,
                # due to invalid credentials or other issues with user-provided credentials.
                if response.status_code == 403:
                    print("Authentication failed")
                    error = ApiForbiddenException(f"Authentication is required for this endpoint, but either credentials were not accepted, or 2FA is required.")
                else:
                    print("Unexpected auth response code: " + str(response.status_code))
                    request_details = "\n\tRequest URL: {}\n\tRequest headers: {}\n\tRequest data: {}".format(
                        auth_url, auth_headers, data)
                    error = ApiCallException(response.status_code, response.text + request_details)
                ApiResource.permanent_auth_failure = error
                raise error
        finally:
            ApiResource.auth_lock.release()

    # Makes a request to Robinhood to retrieve data
    @classmethod
    def request(cls, resource_url, **params):
        request_url = ApiResource.__request_url(resource_url, **params)
        data = None

        if ApiResource.enable_mock and request_url in ApiResource.mock_results:
            # Load the mocked value
            data = ApiResource.mock_results[request_url]
            return data

        if cls.enable_cache:
            # Check if we have a cache hit first
            data = Cache.get(request_url)
            if data:
                return data

        if ApiResource.enable_mock:
            # We have not mocked out a request for this resource, raise an error
            raise NotFoundException(f"Mocking is currently enabled, but Robinhood request has not been mocked: {request_url}")

        headers = {}

        if cls.authenticated:
            access_token = ApiResource.authenticate()

            headers['Authorization'] = 'Bearer ' + access_token

        attempts = 3

        while True:
            attempts -= 1
            try:
                response = requests.get(request_url, headers=headers)
            except requests.exceptions.ConnectionError:
                # Happens occasionally, retry
                if attempts > 0:
                    logger.warn("Warning: Connection error, retrying")
                else:
                    raise ApiInternalErrorException(0, "Repeated connection errors when trying to call Robinhood")
                continue

            if response.status_code != 200:
                print_response(response)

            if response.status_code == 200:
                data = response.json()
                if cls.enable_cache:
                    # Cache response. Only successful calls are cached.
                    Cache.set(request_url, data, cls.cache_timeout)
                return data
            elif response.status_code == 400:
                message = "{} (request URL: {})".format(response.text, request_url)
                raise ApiBadRequestException(message)
            elif response.status_code == 401:
                if cls.authenticated:
                    if attempts > 0:
                        # Credentials may have expired, try reauthenticating
                        access_token = ApiResource.authenticate(force_refresh=True)
                        
                        headers['Authorization'] = 'Bearer ' + access_token
                        continue
                    else:
                        raise ApiUnauthorizedException("Authentication credentials were not accepted")
                else:
                    raise ApiUnauthorizedException("This API endpoint requires authentication: {}".format(cls.endpoint_path))
            elif response.status_code == 403:
                print("Request authentication was rejected; access token likely expired/invalid. Refreshing...")
                if attempts > 0:
                    # Credentials may have expired, try reauthenticating
                    access_token = ApiResource.authenticate(force_refresh=True)

                    headers['Authorization'] = 'Bearer ' + access_token
                    continue
                else:
                    raise ApiForbiddenException("Not authorized to access this resource: {}".format(request_url))
            elif response.status_code == 404:
                return None
            elif response.status_code > 500:
                # Internal server error, retry if possible
                if attempts <= 0:
                    raise ApiInternalErrorException(response.status_code, response.text)
            else:
                raise ApiCallException(response.status_code, response.text)

    @classmethod
    def base_url(cls):
        return ROBINHOOD_ENDPOINT + cls.endpoint_path + "/"

    @classmethod
    def resource_url(cls, resource_id = None):
        url = cls.base_url()
        if resource_id:
            url += "{}/".format(resource_id)
        return url

    @classmethod
    def search_url(cls, **params):
        url = cls.base_url()
        if params:
            param_strs = []
            for key in params:
                # convert list parameters to comma-separated strings
                val = params[key]
                if type(val) in [list, set]:
                    val = ','.join(list(val))
                elif isinstance(val, ApiModel):
                    val = val.url
                param_strs.append("{}={}".format(key, val))

            url += '?' + '&'.join(param_strs)
        return url

    @classmethod
    def mock_get(cls, result, resource_id):
        if re.match("^https:\\/\\/", str(resource_id)):
            resource_url = resource_id
        else:
            resource_url = cls.resource_url(resource_id)
        request_url = ApiResource.__request_url(resource_url)
        ApiResource.__mock(request_url, result.raw_data())

    @classmethod
    def mock_search(cls, results, **params):
        if (type(results)) not in [list, set]:
            results = [results]
        request_url = ApiResource.__request_url(cls.resource_url(), **params)
        ApiResource.__mock(request_url, {
            'results': [r.raw_data() for r in results]
        })

    def __mock(request_url, response):
        ApiResource.mock_results[request_url] = response


    @classmethod
    def has_mock(cls, **params):
        request_url = ApiResource.__request_url(cls.resource_url(), **params)
        return request_url in ApiResource.mock_results

    def __request_url(resource_url: str, **params):
        request_url = resource_url
        # Convert a pathname to a full Robinhood URL
        if resource_url.startswith('/'):
            request_url = ROBINHOOD_ENDPOINT + request_url

        if params:
            param_strs = []
            # Append the keys in sorted order to make cache hits more likely
            # for queries requesting the same items
            for key in sorted(params.keys()):
                # convert list parameters to comma-separated strings
                val = params[key]
                if type(val) == list or type(val) == set:
                    val = ','.join(sorted(str(v) for v in val))
                elif isinstance(val, ApiModel):
                    val = val.url
                param_strs.append("{}={}".format(key, val))

            if '?' in request_url:
                request_url += '&'
            else:
                request_url += '?'
            request_url += '&'.join(param_strs)
        return request_url

    # Enable iteration through the individual items if present
    def __iter__(self):
        try:
            self.__class__.Item
        except NameError:
            raise Exception("Class is not iterable: No Item subclass is defined for this class")

        return iter(self.items)

    def __next__(self):
        return next(self.__iter__())

def print_response(response: Response):
    print(f"{response.status_code} {response.reason}")
    print(f"URL: {response.url}")
    print(f"Response content: '{response.content.decode()}'")
    request_body = response.request.body
    if (request_body and type(request_body) == bytes):
        request_body = request_body.decode()
    print(f"Request content:{request_body}")
    print(f"Request headers: {response.request.headers}")