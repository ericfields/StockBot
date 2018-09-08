import requests
import pandas as pd
from multiprocessing.pool import ThreadPool
from dateutil import parser as dateparser

ROBINHOOD_ENDPOINT = 'https://api.robinhood.com'

class ApiModel():
    attrs = []

    def __init__(self, **data):
        self._assign_attrs(data)

    def _assign_attrs(self, data):
        for attr in self.attrs:
            if attr in data:
                setattr(self, attr, data[attr])
            elif attr not in locals():
                # Initialize all missing attributes as None
                setattr(self, attr, None)

class ApiCallException(Exception):
    pass

class ApiBadRequestException(ApiCallException):
    pass


class ApiResource(ApiModel):
    endpoint_path = ''

    @classmethod
    def get(cls, resource_id):
        data = cls._request(resource_id)
        if data:
            return cls(**data)
        else:
            return None

    @classmethod
    def search(cls, **params):
        data = cls._request(None, **params)
        if data and 'results' in data:
            return [cls(**result) for result in data['results']]

    @classmethod
    def list(cls, resource_id, **params):
        try:
            cls.Item
        except NameError:
            raise Exception("Class is not listable: No Item subclass is defined within this class")

        data = cls._request(resource_id, **params)

        if data:
            obj = cls(**data)
            list_key = cls.__name__.lower()
            if list_key in data:
                obj.items = [cls.Item(**item) for item in data[list_key]]
            return obj
        else:
            return None

    # Retrieve a single instance corresponding to a single resource
    @classmethod
    def _request(cls, resource_id, **params):
        request_url = ROBINHOOD_ENDPOINT + cls.endpoint_path + '/'
        if resource_id:
            request_url += "{}/".format(resource_id)
        if params:
            param_strs = []
            for key in params:
                # convert list parameters to comma-separated strings
                val = params[key]
                if type(val) == list:
                    val = ','.join(val)
                param_strs.append("{}={}".format(key, val))

            request_url += '?' + '&'.join(param_strs)

        response = requests.get(request_url)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            raise ApiBadRequestException(response.text)
        elif response.status_code == 404:
            return None
        else:
            raise ApiCallException(response.text)


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
    attrs = ['symbol', 'last_trade_price']

class Instrument(ApiResource):
    endpoint_path = "/instruments"
    attrs = ['symbol', 'simple_name', 'name']

class Fundamentals(ApiResource):
    endpoint_path = "/fundamentals"
    attrs = ['description']

class Historicals(ApiResource):
    endpoint_path = "/quotes/historicals"
    attrs = ['previous_close_price']

    class Item(ApiModel):
        attrs = ['begins_at', 'close_price']


# Certain chart spans can only be used with certain data intervals.
# This defines each interval to its highest logical resolution.
SPAN_INTERVALS = {
    'day': '5minute',
    'week': '10minute',
    'year': 'day',
    '5year': 'week',
    'all': 'week'
}

def chart_data(symbol, span="day"):
    pool = ThreadPool(processes=1)
    quote_thread_result = pool.apply_async(Quote.get, (symbol,))

    interval = SPAN_INTERVALS[span]

    options = {
        'span': span,
        'interval': interval
    }
    if span == 'day':
        options['bounds'] = 'trading'
    historicals = Historicals.list(symbol, **options)

    time_values = []
    price_values = []
    for historical in historicals:
        time_values.append(dateparser.parse(historical.begins_at))
        price_values.append(float(historical.close_price))

    if historicals.previous_close_price:
        last_closing_price = float(historicals.previous_close_price)
    else:
        last_closing_price = float(historicals.items[0].close_price)

    quote = quote_thread_result.get()
    current_price = float(quote.last_trade_price)

    return pd.Series(price_values, index=time_values), last_closing_price, current_price
