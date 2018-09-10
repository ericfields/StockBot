import requests
from datetime import datetime
from dateutil import parser as dateparser
import pytz
import re

from django.core.cache import cache

ROBINHOOD_ENDPOINT = 'https://api.robinhood.com'

class ApiModel():
    attributes = {}
    cached = False

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
    pass

class ApiBadRequestException(ApiCallException):
    pass


class ApiResource(ApiModel):
    endpoint_path = ''

    @classmethod
    def get(cls, resource_id):
        data = cls.request(cls.resource_url(resource_id))
        if data:
            return cls(**data)
        else:
            return None

    @classmethod
    def search(cls, **params):
        data = cls.request(cls.resource_url(), **params)
        if data and 'results' in data:
            return [cls(**result) for result in data['results']]

    @classmethod
    def list(cls, resource_id, **params):
        try:
            cls.Item
        except NameError:
            raise Exception("Class is not listable: No Item subclass is defined within this class")

        data = cls.request(cls.resource_url(resource_id), **params)

        if data:
            obj = cls(**data)
            list_key = cls.__name__.lower()
            if list_key in data:
                obj.items = [cls.Item(**item) for item in data[list_key]]
            return obj
        else:
            return None

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

        response = None
        if cls.cached:
            response = cache.get(resource_url)
        if not response:
            response = requests.get(resource_url)
            if cls.cached:
                cache.set(resource_url, response)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            raise ApiBadRequestException(response.text)
        elif response.status_code == 404:
            return None
        else:
            raise ApiCallException(response.text)


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

class Quote(ApiResource):
    endpoint_path = "/quotes"
    attributes = {
        'symbol': str,
        'last_trade_price': float
    }

class Instrument(ApiResource):
    endpoint_path = "/instruments"
    cached = True
    attributes = {
        'symbol': str,
        'simple_name': str,
        'name': str
    }

class Fundamentals(ApiResource):
    endpoint_path = "/fundamentals"
    cached = True
    attributes = {
        'description': str
    }

class Historicals(ApiResource):
    endpoint_path = "/quotes/historicals"
    attributes = {
        'previous_close_price': float
    }

    class Item(ApiModel):
        attributes = {
            'begins_at': datetime,
            'close_price': float
        }

class Market(ApiResource):
    endpoint_path = "/markets"
    cached = True
    attributes = {
        'name': str,
        'acronym': str,
        'mic': str,
        'timezone': str
    }

    class Hours(ApiResource):
        endpoint_path = "/hours"
        attributes = {
            'opens_at': datetime,
            'closes_at': datetime,
            'extended_opens_at': datetime,
            'extended_closes_at': datetime,
            'is_open': bool ,
            'previous_open_hours': str
        }

    @classmethod
    def hours(cls, market_mic, date):
        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")
        base_url = cls.resource_url(market_mic)
        resource_url = "{}hours/{}/".format(base_url, date)
        data = cls.request(resource_url)
        if data:
            return Market.Hours(**data)
        else:
            return None
