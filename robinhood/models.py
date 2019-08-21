from robinhood.api import ApiModel, ApiResource
from datetime import datetime, timedelta
from pytz import timezone

class Authentication(ApiResource):
    endpoint_path = "/api-token-auth"

    attributes = {
        'token': str
    }

class HistoricalItem(ApiModel):
    attributes = {
        'begins_at': datetime,
        'open_price': float,
        'close_price': float,
        'interpolated': bool
    }

class NotImplementedException(Exception):
    def __init__(self, calling_class, method_name):
        message = "{} method is not implemented for {}".format(method_name, calling_class)
        super().__init__(message)

class Market(ApiResource):
    endpoint_path = "/markets"
    cache_timeout = 86400

    class Hours(ApiResource):
        cache_timeout = 86400
        attributes = {
            'opens_at': datetime,
            'closes_at': datetime,
            'extended_opens_at': datetime,
            'extended_closes_at': datetime,
            'is_open': bool ,
            'previous_open_hours': ApiResource.CurrentClass
        }

    attributes = {
        'name': str,
        'acronym': str,
        'mic': str,
        'timezone': timezone,
        'todays_hours': Hours
    }

    def hours(self, date = None):
        if not date:
            date = datetime.now(self.timezone)
        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")
        endpoint = "/markets/{}/hours/{}".format(self.mic, date)
        cls = self.__class__.Hours
        return cls(**cls.request(endpoint))

class Instrument(ApiResource):
    # The following methods must be implemented by the inheriting class

    def current_value(self):
        raise NotImplementedException(self.__class__, 'current_value')

    def list_date(self):
        raise NotImplementedException(self.__class__, 'list_date')

    def full_name(self):
        raise NotImplementedException(self.__class__, 'full_name')

    def short_name(self):
        raise NotImplementedException(self.__class__, 'short_name')

    def identifier(self):
        raise NotImplementedException(self.__class__, 'identifier')


    def instrument_url(self):
        if self.id:
            return "{}{}/{}".format(self.api_endpoint, self.endpoint_path, self.id + '/')
        else:
            raise Exception("Cannot return instrument URL; this instrument's ID has not yet been loaded")

    # The following methods do not need to be re-implemented

    def historicals(self, start_date, end_date = None):
        return self.__class__.Historicals.get(self.id, **self.historical_params(start_date, end_date))

    @staticmethod
    def historical_params(start_date, end_date = None):
        if not end_date:
            end_date = datetime.now()

        params = {}

        span = end_date - start_date

        # Determine the highest granularity of data we can request with the given timespan
        if span <= timedelta(days=1):
            params['span'] = 'day'
            params['interval'] = '5minute'
            # Can get request bounds for all trading hours for day charts, instead of just market hours
            params['bounds'] = 'trading'
        elif span <= timedelta(days=7):
            params['span'] = 'week'
            params['interval'] = '10minute'
        elif span <= timedelta(days=365):
            params['span'] = 'year'
            params['interval'] = 'day'
        else:
            params['span'] = '5year'
            params['interval'] = 'week'

        return params

    def __str__(self):
        return self.short_name()

class Stock(Instrument):
    endpoint_path = "/instruments"
    cache_timeout = 86400

    class Quote(ApiResource):
        endpoint_path = "/quotes"
        authenticated = True
        attributes = {
            'symbol': str,
            'last_trade_price': float,
            'last_extended_hours_trade_price': float,
            'updated_at': datetime,
            'instrument': str
        }

        def price(self):
            return self.last_extended_hours_trade_price or self.last_trade_price

    class Fundamentals(ApiResource):
        endpoint_path = "/fundamentals"
        cache_timeout = 86400
        attributes = {
            'description': str
        }

    class Historicals(ApiResource):
        endpoint_path = "/quotes/historicals"
        authenticated = True
        cache_timeout = 300

        attributes = {
            'previous_close_price': float,
            'instrument': str,
        }

        class Item(HistoricalItem):
            list_key = 'historicals'
            pass

    attributes = {
        'id': str,
        'symbol': str,
        'simple_name': str,
        'name': str,
        'list_date': datetime,
        'tradable_chain_id': str,
        'fundamentals': Fundamentals,
        'quote': Quote,
        'market': Market,
        'url': str,
        'tradeable': bool,
        'state': str
    }

    def current_value(self):
        return self.quote().last_trade_price

    def list_date(self):
        return self.list_date

    def full_name(self):
        return "{} ({})".format(self.name, self.symbol)

    def short_name(self):
        return self.simple_name

    def identifier(self):
        return self.symbol

class Option(Instrument):
    endpoint_path = "/options/instruments"
    cache_timeout = 86400
    attributes = {
        'id': str,
        'issue_date': datetime,
        'tradability': str,
        'strike_price': float,
        'expiration_date': datetime,
        'chain_id': str,
        'type': str,
        'chain_symbol': str,
        'url': str,
        'tradeable': bool,
        'state': str
    }

    class Quote(ApiResource):
        endpoint_path = "/marketdata/options"
        authenticated = True
        attributes = {
            'adjusted_mark_price': float,
            'previous_close_price': float,
            'instrument': str
        }

        def price(self):
            return self.adjusted_mark_price

    class Historicals(ApiResource):
        endpoint_path = "/marketdata/options/historicals"
        authenticated = True
        cache_timeout = 300

        attributes = {
            'instrument': str
        }

        class Item(HistoricalItem):
            list_key = 'data_points'
            pass

    def quote(self):
        return self.__class__.Quote.get(self.id)

    def current_value(self):
        return self.quote().adjusted_mark_price

    def list_date(self):
        return self.issue_date

    def full_name(self):
        symbol = self.chain_symbol
        price = self.strike_price
        if price % 1 > 0:
            price = round(price, 1)
        else:
            price = round(price)
        type = self.type.capitalize()
        expiration = self.expiration_date.strftime("%D")

        return "{} ${} {} exp. {}".format(symbol, price, type, expiration)

    def short_name(self):
        type = self.type[0].upper()
        expiration = self.expiration_date.strftime("%D")
        price = self.strike_price
        if price % 1 > 0:
            price = round(price, 1)
        else:
            price = round(price)
        symbol = self.chain_symbol

        return "{} ${}{} {}".format(symbol, price, type, expiration)

    def identifier(self):
        type = self.type[0].upper()
        expiration = self.expiration_date.strftime("%D")
        price = round(self.strike_price, 1)
        symbol = self.chain_symbol
        return "{}{}{}@{}".format(symbol, price, type, expiration)

class NewsItem(ApiModel):
    attributes = {
        'url': str,
        'api_source': str,
        'source': str,
        'summary': str,
        'title': str,
        'author': str,
        'instrument': Instrument,
        'num_clicks': int,
        'preview_image_url': str,
        'published_at': datetime,
        'updated_at': datetime,
        'relay_url': str,
        'related_instruments': list
    }

class News(ApiResource):
    endpoint_path = "/midlands/news"

    class Item(NewsItem):
        list_key = 'results'
