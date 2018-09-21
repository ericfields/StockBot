from .models import User, Portfolio, Security
from .stock_quote_handler import StockQuoteHandler
from .option_quote_handler import OptionQuoteHandler
from .utilities import mattermost_text
from .exceptions import BadRequestException
from .views import find_instrument
import re

QUOTE_HANDLERS = [StockQuoteHandler, OptionQuoteHandler]

def get_portfolio(request):
    user = get_or_create_user(request)

    try:
        portfolio = Portfolio.objects.get(user=user)
    except Portfolio.DoesNotExist:
        raise BadRequestException("You don't have a portfolio")

    securities = portfolio.security_set.all()

    response = "{}:\n{}".format(portfolio.symbol, securities_to_str(securities))
    return mattermost_text(response)

def create_portfolio(request):
    usage_str = "Usage: command-name portfolio_symbol"

    body = request.POST.get('text', None)
    if not body:
        raise BadRequestException(usage_str)
    parts = body.split(' ')
    if len(parts) == 0 or not parts[0]:
        raise BadRequestException(usage_str)

    symbol = parts[0].upper()
    if not re.match('^[A-Z]{1,14}$', symbol):
        raise BadRequestException("Name must be a string of letters no longer than 14 characters")

    user = get_or_create_user(request)

    # Ensure that user only has one portfolio (for now)
    portfolio = get_or_create_portfolio(user, symbol)
    return mattermost_text("Portfolio ready: {}".format(symbol))

def delete_portfolio(request):
    user = get_or_create_user(request)
    portfolio = get_or_create_portfolio(user)
    portfolio.delete()
    return mattermost_text("{} deleted.".format(portfolio.symbol))

def add_to_portfolio(request):
    return modify_portfolio(request)

def remove_from_portfolio(request):
    return modify_portfolio(request, True)

def modify_portfolio(request, remove_assets = False):
    usage_str = "Usage: command-name [stock1:count, option1: count...]"

    user = get_or_create_user(request)
    portfolio = get_or_create_portfolio(user)

    body = request.POST.get('text', None)
    if not body:
        raise BadRequestException(usage_str)

    securities_to_save = []

    security_defs = re.split('[\s,]+', body)
    for sd in security_defs:
        parts = re.split('[:=]', sd)
        if not parts:
            raise BadRequestException("Invalid definition: '{}'".format(sd))
        identifier = parts[0]
        if len(parts) > 1:
            try:
                count = float(parts[1])
            except ValueError:
                raise BadRequestException("Invalid count: '{}'".format(parts[1]))
        else:
            count = 1

        security = get_or_create_security(portfolio, identifier)

        if remove_assets:
            if count > security.count:
                if count % 1 == 0:
                    count = round(count)
                type = security.get_type_display()
                raise BadRequestException("You do not have {} {} {}(s) to sell in your portfolio".format(count, identifier, type))
            security.count -= count
        else:
            security.count += count
        securities_to_save.append(security)

    # Wait until all securities have been validated before saving
    for s in securities_to_save:
        if s.count <= 0:
            s.delete()
        else:
            s.save()

    response = "New portfolio:\n{}".format(securities_to_str(portfolio.security_set.all()))
    return mattermost_text(response)

def get_or_create_security(portfolio, identifier):
    instrument = find_instrument(identifier)
    try:
        return Security.objects.get(portfolio=portfolio, instrument_id=instrument.id)
    except Security.DoesNotExist:
        for handler in QUOTE_HANDLERS:
            if re.match(handler.FORMAT, identifier):
                type = handler.TYPE
        return Security(portfolio=portfolio, instrument_id=instrument.id,
            identifier=instrument.identifier(), type=type[0].upper(), count=0)

def get_or_create_user(request):
    user_id = request.POST.get('user_id', None)
    user_name = request.POST.get('user_name', None)

    if not user_id:
        raise BadRequestException("user_id is not present")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        if not user_name:
            raise BadRequestException("user_name is not present")
        user = User(id=user_id, name=user_name)
        user.save()
    return user

def get_or_create_portfolio(user, symbol = None):
    portfolio = None
    if symbol: # We can create the portfolio if it does not exist
        try:
            portfolio = Portfolio.objects.get(symbol=symbol)
            if portfolio.user_id != user.id:
                raise BadRequestException("{} belongs to {}".format(symbol, portfolio.user.name))
        except Portfolio.DoesNotExist:
            # Replace the user's current portfolio symbol if it exists
            try:
                portfolio = Portfolio.objects.get(user=user)
            except Portfolio.DoesNotExist:
                portfolio = Portfolio(user=user)
            # Verify that this portfolio name does not match an instrument name
            instrument = None
            try:
                instrument = find_instrument(symbol)
            except BadRequestException:
                # Instrument doesn't exist
                pass
            if instrument:
                raise BadRequestException("Can't use this name; a stock named {} already exists".format(symbol))

            portfolio.symbol = symbol
            portfolio.save()
    else:
        try:
            portfolio = Portfolio.objects.get(user=user)
        except Portfolio.DoesNotExist:
            raise BadRequestException("You don't have a portfolio.")
    return portfolio

def securities_to_str(securities):
    security_strs = []
    for s in securities:
        security_str = s.identifier + ': '
        if s.count % 1 == 0:
            security_str += str(round(s.count))
        else:
            security_str += str(s.count)
        security_strs.append(security_str)
    return "\n".join(security_strs)
