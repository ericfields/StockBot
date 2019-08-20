from .instrument_handler import InstrumentHandler
from robinhood.models import Option
from dateutil import parser as dateparser
from exceptions import BadRequestException
import re

class OptionHandler(InstrumentHandler):

    TYPE = 'option'
    FORMAT = '^([A-Z\.]+)\$?([0-9]+(\.[05]0?)?)([CP])@?([0-9\/\-]+)?$'
    EXAMPLE = "AAPL250.5C@12-21"

    def instrument_class(self):
        return Option

    def get_search_params(self, identifier):
        symbol, price, type, expiration_date = self.parse_option(identifier)

        params = {
            'chain_symbol': symbol,
            'strike_price': price,
            'type': type,
            # Note: currently options in the Robinhood API cannot be searched
            # based on their expiration date. This field is really only set for
            # caching purposes. Robinhood will simply ignore it.
            'expiration_date': expiration_date
        }
        if not expiration_date:
            # No expiration date provided, get options for the end of the week.
            # Need to ensure that only active options are returned.
            params['state'] = 'active'

        return params

    def authenticated(self):
        return True

    def filter_results(self, instruments, params):
        # Sort options in order of expiration date
        instruments.sort(key=lambda o: o.expiration_date)

        results = []

        if 'expiration_date' in params and params['expiration_date']:
            for instrument in instruments:
                if instrument.state == "inactive": # Removed or deactivated, not expired
                    continue
                if instrument.expiration_date == params['expiration_date']:
                     results.append(instrument)
        else:
            # Get the option expiring earliest, i.e. an "FD"
            results = [instruments[0]]

        return results


    def standard_identifier(self, identifier):
        symbol, price, type, expiration_date = self.parse_option(identifier)
        standard = "{}{}{}".format(symbol, round(price, 1), type[0].upper())
        if expiration_date:
            standard += "@" + expiration_date.strftime("%D")
        return standard

    def parse_option(self, option_str):
        match = re.match(self.FORMAT, option_str)
        if not match:
            raise BadRequestException("Not a valid option identifier: {}".format(option_str))

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
            expiration = self.parse_expiration_date(expiration)

        return symbol, price, type, expiration

    def parse_expiration_date(self, date_str):
        # Convert from simple 4-digit and 8-digit formats
        if re.match('^[0-9]{4}$', date_str):
            date_str = '/'.join([date_str[0:2], date_str[2:4]])
        elif re.match('^[0-9]{8}$', date_str):
            date_str = '/'.join([date_str[0:2], date_str[2:4], date_str[4:8]])

        try:
            return dateparser.parse(date_str)
        except ValueError:
            raise BadRequestException("Invalid date: '{}'".format(date_str))
