from robinhood.api import ApiModel, ApiResource
from datetime import datetime

class Authentication(ApiResource):
    endpoint_path = "/api-token-auth"

    attributes = {
        'token': str
    }

class Quote(ApiResource):
    endpoint_path = "/quotes"
    attributes = {
        'symbol': str,
        'last_trade_price': float,
        'last_extended_hours_trade_price': float,
        'updated_at': datetime,
        'instrument': str
    }

class Instrument(ApiResource):
    endpoint_path = "/instruments"
    cached = True
    attributes = {
        'id': str,
        'symbol': str,
        'simple_name': str,
        'name': str,
        'list_date': datetime,
        'tradable_chain_id': str,
        'url': str
    }

    def full_name(self):
        return "{} ({})".format(
            self.simple_name or self.name,
            self.symbol
        )

    def short_name(self):
        return self.symbol

    def identifier(self):
        return self.symbol

    def __str__(self):
        return self.simple_name()

class Fundamentals(ApiResource):
    endpoint_path = "/fundamentals"
    cached = True
    attributes = {
        'description': str
    }

class HistoricalItem(ApiModel):
    attributes = {
        'begins_at': datetime,
        'open_price': float,
        'close_price': float,
        'interpolated': bool
    }

class Historicals(ApiResource):
    endpoint_path = "/quotes/historicals"
    attributes = {
        'previous_close_price': float,
        'instrument': str
    }

    class Item(HistoricalItem):
        list_key = 'historicals'
        pass

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
        cached = True
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

class OptionInstrument(ApiResource):
    endpoint_path = "/options/instruments"
    cached = True
    attributes = {
        'id': str,
        'issue_date': datetime,
        'tradability': str,
        'strike_price': float,
        'expiration_date': datetime,
        'chain_id': str,
        'type': str,
        'chain_symbol': str,
        'url': str
    }

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
        expiration = self.expiration_date.strftime("%-m/%-d")
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

    def __str__(self):
        return self.simple_name()

class OptionQuote(ApiResource):
    endpoint_path = "/marketdata/options"
    authenticated = True
    attributes = {
        'adjusted_mark_price': float,
        'previous_close_price': float,
        'instrument': str
    }

class OptionHistoricals(ApiResource):
    endpoint_path = "/marketdata/options/historicals"
    authenticated = True

    attributes = {
        'instrument': str
    }

    class Item(HistoricalItem):
        list_key = 'data_points'
        pass
