from .handler import Handler
from robinhood.api import ApiResource
from robinhood.models import Option
from .exceptions import BadRequestException, ConfigurationException
from .stock_handler import StockHandler
from dateutil import parser as dateparser
import re

class OptionHandler(Handler):

    TYPE = 'option'
    FORMAT = '^([A-Z\.]+)([0-9]+(\.[05]0?)?)([CP])@?([0-9\/\-]+)?$'
    EXAMPLE = "AAPL250.5C@12-21"

    def get_instrument(instrument_uuid):
        OptionHandler.check_authentication()
        return Option.get(instrument_uuid)

    def search_for_instrument(identifier):
        OptionHandler.check_authentication()
        symbol, price, type, expiration = OptionHandler.parse_option(identifier)

        stock_instrument = StockHandler.search_for_instrument(symbol)

        instruments = Option.search(
            chain_id=stock_instrument.tradable_chain_id,
            strike_price=price,
            type=type,
            state='active'
        )

        instrument = None

        # Sort options in order of expiration date
        if instruments:
            instruments.sort(key=lambda o: o.expiration_date)

            if expiration:
                try:
                    instrument = next(i for i in instruments if i.expiration_date == expiration)
                except StopIteration:
                    pass
            else:
                # Get the option expiring earliest, i.e. an "FD"
                instrument = instruments[0]

        if not instrument:
            message = "No tradeable {} ${} {} option".format(symbol, round(price, 1), type)
            if expiration:
                message += " expiring {}".format(expiration.strftime("%-x"))
            raise BadRequestException(message)

        return instrument

    def check_authentication():
        if not (ApiResource.username and ApiResource.password):
            raise ConfigurationException("This command requires an authenticated backend API call, but credentials are not configured for this server.")

    def parse_option(option_str):
        match = re.match(OptionHandler.FORMAT, option_str)

        parts = match.groups()

        symbol = parts[0]
        price = float(parts[1])
        if parts[3] == 'C':
            type = 'call'
        else:
            type = 'put'
        expiration = parts[4]

        if expiration:
            # Parse expiration date string
            expiration = OptionHandler.parse_expiration_date(expiration)

        return symbol, price, type, expiration

    def parse_expiration_date(date_str):
        # Convert from simple 4-digit and 8-digit formats
        if re.match('^[0-9]{4}$', date_str):
            date_str = '/'.join([date_str[0:2], date_str[2:4]])
        elif re.match('^[0-9]{8}$', date_str):
            date_str = '/'.join([date_str[0:2], date_str[2:4], date_str[4:8]])

        try:
            return dateparser.parse(date_str)
        except ValueError:
            raise BadRequestException("Invalid date: '{}'".format(date_str))
