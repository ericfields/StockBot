import requests
from datetime import datetime
from dateutil import parser as dateparser
import pytz
import re
import json
from threading import Lock

from django.core.cache import cache

ROBINHOOD_ENDPOINT = 'https://api.robinhood.com'

class ApiModel():
    attributes = {}
    username = None
    password = None
    client_id = None
    api_token = None
    refresh_token = None

    def __init__(self, **data):
        self._assign_attributes(data)

    def _assign_attributes(self, data):
        for attr in self.attributes:
            if attr in data:
                val = self._typed_attribute(attr, data[attr])
                setattr(self, attr, val)
            elif attr not in locals():
                # Initialize all missing attributes as None
                setattr(self, attr, None)

    def _typed_attribute(self, attr, val):
        if val == None:
            return val
        type = self.attributes[attr]
        if type == None:
            return val
        elif type == str:
            return str(val)
        elif type == float:
            return float(val)
        elif type == val:
            return int()
        elif type == datetime:
            date = dateparser.parse(val).astimezone(pytz.utc).replace(tzinfo=None)
            return date
        elif type == bool:
            return val in [True, 'true', 'True', 't', 1]
        else:
            return type(val)

class ApiCallException(Exception):
    code = None

    def __init__(self, code, message):
        self.code = code
        message = "{}: {}".format(code, message)
        super().__init__(message)

class ApiInternalErrorException(ApiCallException):
    pass

class ApiForbiddenException(ApiCallException):
    def __init__(self, message = None):
        if not message:
            message = "Authentication expired or not provided"
        super().__init__(403, message)

class ApiBadRequestException(ApiCallException):
    def __init__(self, message):
        super().__init__(400, message)


class ApiResource(ApiModel):
    endpoint_path = ''
    authenticated = False
    cached = False

    # State variable to set while we are renewing our auth credentials
    auth_lock = Lock()

    @classmethod
    def get(cls, resource_id):
        data = cls.request(cls.resource_url(resource_id))
        if data:
            return cls(**data)
        else:
            return None

    @classmethod
    def search(cls, **params):
        results = []
        data = cls.request(cls.resource_url(), **params)
        while data and 'results' in data:
            results.extend([cls(**result) for result in data['results']])
            if 'next' in data and data['next']:
                # Keep requesting until all data has been returned
                next_url = re.sub('\/', '/', data['next'])
                data = cls.request(next_url)
            else:
                break

        return results

    @classmethod
    def list(cls, resource_id, **params):
        try:
            cls.Item
        except NameError:
            raise Exception("Class is not listable: No Item subclass is defined within this class")

        list_key = cls.Item.list_key
        data = cls.request(cls.resource_url(resource_id), **params)
        if data:
            obj = cls(**data)
            if list_key in data:
                obj.items = [cls.Item(**item) for item in data[list_key]]
            return obj
        else:
            return None

    @staticmethod
    def authenticate():
        auth_url = ROBINHOOD_ENDPOINT + "/oauth2/token/"
        if ApiResource.refresh_token:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': ApiResource.refresh_token,
                'client_id': ApiResource.client_id
            }
        else:
            data={
                'grant_type': 'password',
                'expires_in': 86400,
                'username': ApiResource.username,
                'password': ApiResource.password,
                'client_id': ApiResource.client_id,
                'scope': 'internal'
            }

        attempts = 3

        ApiResource.auth_lock.acquire()
        try:
            if not ApiResource.api_token:
                while True:
                    try:
                        response = requests.post(auth_url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))
                        break
                    except requests.exceptions.ConnectionError:
                        # Happens occasionally, retry
                        attempts -= 1
                        continue

                if response.status_code != 200:
                    ApiResource.api_token = None
                    raise ApiForbiddenException(response.text)

                data = response.json()
                ApiResource.api_token = data['access_token']
                ApiResource.refresh_token = data['refresh_token']
                return True
        finally:
            ApiResource.auth_lock.release()

    # Makes a request to Robinhood to retrieve data
    @classmethod
    def request(cls, resource_url, **params):
        if params:
            param_strs = []
            for key in params:
                # convert list parameters to comma-separated strings
                val = params[key]
                if type(val) == list:
                    val = ','.join(val)
                param_strs.append("{}={}".format(key, val))

            resource_url += '?' + '&'.join(param_strs)

        if cls.cached:
            # Check if we have a cache hit first
            response = cache.get(resource_url)
            if response:
                return response.json()

        attempts = 3

        headers = {}

        while True:
            if cls.authenticated:
                if ApiResource.api_token:
                    headers['Authorization'] = 'Bearer ' + ApiResource.api_token
                else:
                    ApiResource.authenticate()

            try:
                response = requests.get(resource_url, headers=headers)
            except requests.exceptions.ConnectionError:
                # Happens occasionally, retry
                attempts -= 1
                if attempts <= 0:
                    raise ApiInternalErrorException(response.status_code, response.text)
                continue

            if response.status_code == 200:
                if cls.cached:
                    # Cache response. Only successful calls are cached.
                    cache.set(resource_url, response)

                return response.json()
            elif response.status_code == 400:
                raise ApiBadRequestException(response.text)
            elif response.status_code == 403:
                # Authentication may be expired, refresh credentials and retry
                ApiResource.authenticate()
            elif response.status_code == 404:
                return None
            elif response.status_code > 500:
                # Internal server error, retry
                attempts -= 1
                if attempts <= 0:
                    raise ApiInternalErrorException(response.status_code, response.text)
            else:
                raise ApiCallException(response.status_code, response.text)

    @classmethod
    def resource_url(cls, resource_id = None):
        resource_url = ROBINHOOD_ENDPOINT + cls.endpoint_path + "/"
        if resource_id:
            resource_url += "{}/".format(resource_id)
        return resource_url

    # Enable iteration through the individual items if present
    def __iter__(self):
        try:
            self.__class__.Item
        except NameError:
            raise Exception("Class is not iterable: No Item subclass is defined for this class")

        return iter(self.items)

    def __next__(self):
        return next(__iter__())
