from .models import User, Portfolio, Security
from .stock_handler import StockHandler
from .option_handler import OptionHandler
from .utilities import mattermost_text, find_instrument
from .exceptions import BadRequestException
from robinhood.models import Stock, Option
import re

def portfolio(request):
    if request.POST.get('text', None):
        return portfolio_action(request)
    else:
        return display_portfolio(request)

def portfolio_action(request):
    usage_str = """Usage:
/portfolio create [symbol] [$cash] [stock1:count, [stock2: count, [option1: count...]]]
/portfolio rename [symbol]
/portfolio add [$cash] [stock1:count, [stock2: count, [option1: count...]]]
/portfolio remove [$cash] [stock1:count, [stock2: count, [option1: count...]]]
/portfolio buy [stock1:count, [stock2: count, [option1: count...]]]
/portfolio sell [stock1:count, [stock2: count, [option1: count...]]]
/portfolio destroy
"""

    body = request.POST.get('text', None)
    parts = re.split('[,\s]+', body)

    command = parts[0].lower()
    parts.pop(0)

    remove_assets = False
    maintain_value = False

    user = get_or_create_user(request)

    if command not in ['create', 'rename', 'destroy', 'add', 'remove', 'buy', 'sell']:
        raise BadRequestException(usage_str)

    if command == 'create':
        return create_portfolio(user, parts)
    else:
        portfolio = get_or_create_portfolio(user)

    if command == 'rename':
        # Check for portfolio symbol
        if not parts:
            raise BadRequestException("Usage: /portfolio rename [symbol]")

        symbol = parts[0].upper()
        if verify_symbol(symbol):
            portfolio.symbol = symbol
            portfolio.save()
            return mattermost_text("Portfolio renamed to {}".format(symbol))
        else:
            raise BadRequestException("Invalid symbol: '{}'. Symbol must be an alphabetic string no longer than 14 characters.".format(symbol))

    if command == 'destroy':
        return delete_portfolio(portfolio)

    remove_assets = False
    maintain_value = False

    if command == 'remove':
        remove_assets = True
    elif command == 'buy':
        maintain_value = True
    elif command == 'sell':
        maintain_value = True
        remove_assets = True

    return update_portfolio(portfolio, parts, remove_assets=remove_assets, maintain_value=maintain_value)

def display_portfolio(request):
    user = get_or_create_user(request)

    try:
        portfolio = Portfolio.objects.get(user=user)
    except Portfolio.DoesNotExist:
        raise BadRequestException("You don't have a portfolio")

    return print_portfolio(portfolio)

def create_portfolio(user, parts):
    usage_str = "Usage: /portfolio create [symbol] [$cash] [stock1:count, [stock2: count, [option1: count...]]]"

    if not parts:
        raise BadRequestException(usage_str)

    # Check for portfolio symbol
    if verify_symbol(parts[0]):
        symbol = parts[0].upper()
        portfolio = get_or_create_portfolio(user, symbol)
        parts.pop(0)
    else:
        # Get the user's existing portfolio, if present
        portfolio = get_or_create_portfolio(user)

    return update_portfolio(portfolio, parts, replace_securities=True)

def delete_portfolio(portfolio):
    portfolio.delete()
    return mattermost_text("{} deleted.".format(portfolio.symbol))

def update_portfolio(portfolio, security_defs, **opts):
    # Check for initial cash amount
    if security_defs and re.match('^\$[0-9]+(\.[0-9]{2})?$', security_defs[0]):
        cash_value = float(security_defs[0].replace('$', ''))
        if cash_value > 1000000000:
            raise BadRequestException("Highly doubt you have over a billion dollars in cash")
        portfolio.cash = cash_value
        security_defs.pop(0)

    process_securities(portfolio, security_defs, **opts)

    return print_portfolio(portfolio)

def process_securities(portfolio, security_defs, remove_assets = False, maintain_value = False, replace_securities = False):
    securities_to_save = []
    for sd in security_defs:
        parts = re.split('[:=]', sd)
        if not parts:
            raise BadRequestException("Invalid definition: '{}'".format(sd))
        identifier = parts[0]
        if len(parts) > 1:
            try:
                count = float(parts[1])
                if count > 1000000000:
                    raise BadRequestException("Highly doubt you have over a billion shares")
            except ValueError:
                raise BadRequestException("Invalid count: '{}'".format(parts[1]))
        else:
            count = 1

        security = get_or_create_security(portfolio, identifier)

        if replace_securities:
            # Ensure the count starts at 0 since it's being replaced
            security.count = 0

        cash_value = security.instrument().current_value() * count

        if remove_assets:
            if count > security.count:
                if count % 1 == 0:
                    count = round(count)
                type = security.get_type_display()
                raise BadRequestException("You do not have {} {} {}(s) to sell in your portfolio".format(count, identifier, type))
            security.count -= count
            if maintain_value:
                portfolio.cash -= cash_value
        else:
            if maintain_value:
                if portfolio.cash < cash_value:
                    raise BadRequestException("You do not have enough cash to buy {} {} {}s. You must have at least ${:,.2f} in your portfolio to buy these (you currently have ${:,.2f}).".format(
                        count, identifier, security.get_type_display(), cash_value, portfolio.cash
                    ))
                portfolio.cash -= cash_value

            security.count += count

        securities_to_save.append(security)

    # Wait until all transactions have been validated before modifying the database

    if replace_securities:
        # Delete any securites not specified in this request
        new_security_ids = [s.id for s in securities_to_save]
        for s in portfolio.security_set.all():
            if not s._state.adding and s.id not in new_security_ids:
                s.delete()

    for s in securities_to_save:
        if s.count <= 0:
            s.delete()
        else:
            s.save()

    portfolio.save()


def get_or_create_security(portfolio, identifier):
    instrument = find_instrument(identifier)
    try:
        return Security.objects.get(portfolio=portfolio, instrument_id=instrument.id)
    except Security.DoesNotExist:
        if isinstance(instrument, Stock):
            type = Security.STOCK
        elif isinstance(instrument, Option):
            type = Security.OPTION
        else:
            raise Exception("No Security type defined for instrument of type '{}''".format(type(instrument)))

        return Security(portfolio=portfolio, instrument_id=instrument.id,
            identifier=instrument.identifier(), type=type, count=0)

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

            # Verify that this portfolio name does not match a stock name
            if Stock.search(symbol=symbol):
                raise BadRequestException("Can't use this name; a stock named {} already exists".format(symbol))

            portfolio.symbol = symbol
            portfolio.save()
    else:
        try:
            portfolio = Portfolio.objects.get(user=user)
        except Portfolio.DoesNotExist:
            raise BadRequestException("You don't have a portfolio.")
    return portfolio

def verify_symbol(symbol):
    symbol = symbol.upper()
    if re.match('^[A-Z]{1,14}$', symbol):
        return True
    else:
        return False


def print_portfolio(portfolio):
    securities = portfolio.security_set.all()
    cash_value = portfolio.cash
    total_value = sum([s.current_value() for s in securities]) + cash_value
    response = "{} (${:,.2f}):\n\tCash: ${:,.2f}\n\t{}".format(
        portfolio.symbol, total_value, cash_value, securities_to_str(securities)
    )
    return mattermost_text(response)

def securities_to_str(securities):
    security_strs = []
    for s in securities:
        security_str = s.identifier + ': '
        if s.count % 1 == 0:
            security_str += str(round(s.count))
        else:
            security_str += str(s.count)
        security_strs.append(security_str)
    if not security_strs:
        return "No assets in portfolio"
    return "\n\t".join(security_strs)
