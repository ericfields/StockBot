import requests
from datetime import datetime, timedelta
from dateutil import parser as dateparser
import pytz
import re
import json
from threading import Lock
from time import sleep
import hashlib
import logging
from time import time
from helpers.cache import Cache

ROBINHOOD_ENDPOINT = 'https://api.robinhood.com'

logger = logging.getLogger('stockbot')

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
        try:
            item_class = self.__class__.Item
            list_key = item_class.list_key
            if list_key in data:
                self.items = [item_class(**item) for item in data[list_key]]
        except AttributeError:
            # Not a listable item class
            pass

    def __typed_attribute(self, attr, val):
        if val == None:
            return val
        attr_type = self.attributes[attr]
        if attr_type == None:
            return val
        elif attr_type == datetime:
            date = dateparser.parse(val).astimezone(pytz.utc).replace(tzinfo=None)
            return date
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
            return attr_type(val)

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

    enable_cache = True
    cache_timeout = None

    @classmethod
    def search(cls, **params):
        results = []
        data = cls.request(cls.resource_url(), **params)
        while data and 'results' in data:
            results.extend([cls(**result) for result in data['results'] if result])
            if 'next' in data and data['next']:
                # Keep requesting until all data has been returned
                next_url = re.sub('\/', '/', data['next'])
                data = cls.request(next_url)
            else:
                break

        return results

    @classmethod
    def get(cls, resource_id, **params):
        if re.match("^https:\/\/", str(resource_id)):
            resource_url = resource_id
        else:
            resource_url = cls.resource_url(resource_id)
        data = cls.request(resource_url, **params)
        if data:
            return cls(**data)
        else:
            return None


    @staticmethod
    def authenticate():
        if not (ApiResource.username and ApiResource.password and ApiResource.device_token and ApiResource.oauth_client_id):
            raise RobinhoodCredentialsException("Attempting to call authenticated endpoint, but one or more Robinhood credentials are missing for this server.")

        # If authentication has already failed, do not try again
        if ApiResource.permanent_auth_failure:
            raise ApiResource.permanent_auth_failure

        auth_url = ROBINHOOD_ENDPOINT + "/oauth2/token/"

        auth_request_headers = {
            'Content-Type': 'application/json',
            'X-Robinhood-API-Version': '1.265.0'
        }

        refresh_token = Cache.get('auth_refresh_token')

        attempts = 3

        while True:
            attempts -= 1

            if refresh_token:
                data = {
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                    'client_id': ApiResource.oauth_client_id,
                    'device_token': ApiResource.device_token
                }
            else:
                data = {
                    'grant_type': 'password',
                    'expires_in': 86400,
                    'username': ApiResource.username,
                    'password': ApiResource.password,
                    'client_id': ApiResource.oauth_client_id,
                    'device_token': ApiResource.device_token,
                    'scope': 'internal'
                }

            try:
                response = requests.post(auth_url, headers=auth_request_headers, data=json.dumps(data))
            except requests.exceptions.ConnectionError as e:
                # Occasional error, retry if possible
                if attempts > 0:
                    sleep(1)
                    continue

                raise e


            if response.status_code == 200:
                data = response.json()

                access_token = data['access_token']
                refresh_token = data['refresh_token']

                Cache.set('auth_access_token', access_token)
                Cache.set('auth_refresh_token', refresh_token)

                return access_token

            if response.status_code >= 500:
                if attempts > 0:
                    sleep(1)
                    continue

                raise ApiInternalErrorException(response.status_code, response.text)

            if response.status_code == 401:
                try:
                    response_data = response.json()
                    if 'error' in response_data and response_data['error'] == 'invalid_grant':
                        # Refresh token is no longer valid
                        # Remove it and re-attempt authentication with username/password
                        refresh_token = None
                        continue
                except ValueError:
                    # Response is not valid JSON, let remaining error logic handle it
                    pass

            if response.status_code == 429:
                raise ApiThrottledException(response.text)

            # Error codes other than these are considered to be permanent errors,
            # due to invalid credentials or other issues with user-provided credentials.
            if response.status_code == 403:
                error = ApiForbiddenException("Authentication is required for this endpoint, but credentials are expired or invalid.")
            else:
                request_details = "\n\tRequest URL: {}\n\tRequest headers: {}\n\tRequest data: {}".format(
                    auth_url, auth_request_headers, data)
                error = ApiCallException(response.status_code, response.text + request_details)
            ApiResource.permanent_auth_failure = error
            raise error

    # Makes a request to Robinhood to retrieve data
    @classmethod
    def request(cls, resource_url, **params):
        # Convert a pathname to a full Robinhood URL
        if re.match('^\/', resource_url):
            resource_url = ROBINHOOD_ENDPOINT + resource_url

        if params:
            param_strs = []
            for key in params:
                # convert list parameters to comma-separated strings
                val = params[key]
                if type(val) == list or type(val) == set:
                    val = ','.join(str(v) for v in val)
                elif isinstance(val, ApiModel):
                    val = val.url
                param_strs.append("{}={}".format(key, val))

            resource_url += '?' + '&'.join(param_strs)

        data = None
        if cls.enable_cache:
            # Check if we have a cache hit first
            data = Cache.get(resource_url)
            if data:
                return data

        headers = {}

        if cls.authenticated:
            access_token = Cache.get('auth_access_token')
            if not access_token:
                access_token = ApiResource.authenticate()

            headers['Authorization'] = 'Bearer ' + access_token

        attempts = 3

        while True:
            attempts -= 1
            try:
                start_time = time()
                #cls.print_request(resource_url, headers)
                response = requests.get(resource_url, headers=headers)
            except requests.exceptions.ConnectionError:
                # Happens occasionally, retry
                if attempts > 0:
                    logger.warn("Warning: Connection error, retrying")
                else:
                    raise ApiInternalErrorException(0, "Repeated connection errors when trying to call Robinhood")
                continue

            if response.status_code == 200:
                data = response.json()
                if cls.enable_cache:
                    # Cache response. Only successful calls are cached.
                    Cache.set(resource_url, data, cls.cache_timeout)
                return data
            elif response.status_code == 400:
                message = "{} (request URL: {})".format(response.text, resource_url)
                raise ApiBadRequestException(message)
            elif response.status_code == 401:
                if cls.authenticated:
                    if attempts > 0:
                        # Credentials may have expired, try reauthenticating
                        access_token = ApiResource.authenticate()
                        headers['Authorization'] = 'Bearer ' + access_token
                        continue
                    else:
                        raise ApiUnauthorizedException("Authentication credentials were not accepted")
                else:
                    raise ApiUnauthorizedException("This API endpoint requires authentication: {}".format(cls.endpoint_path))
            elif response.status_code == 403:
                if attempts > 0:
                    # Credentials may have expired, try reauthenticating
                    access_token = ApiResource.authenticate()
                    headers['Authorization'] = 'Bearer ' + access_token
                    continue
                else:
                    raise ApiForbiddenException("Not authorized to access this resource: {}".format(resource_url))
            elif response.status_code == 404:
                return None
            elif response.status_code > 500:
                # Internal server error, retry if possible
                if attempts <= 0:
                    raise ApiInternalErrorException(response.status_code, response.text)
            else:
                raise ApiCallException(response.status_code, response.text)

    @classmethod
    def print_request(cls, url, headers=None):
        print("Request: {}".format(url))
        if headers:
            for h in headers:
                print("\n\t{}: {}".format(h, headers[h]))


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

    # Enable iteration through the individual items if present
    def __iter__(self):
        try:
            self.__class__.Item
        except NameError:
            raise Exception("Class is not iterable: No Item subclass is defined for this class")

        return iter(self.items)

    def __next__(self):
        return next(__iter__())
