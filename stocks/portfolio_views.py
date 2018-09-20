from .models import User, Portfolio, Security
from .stock_views import SYMBOL_FORMAT, find_stock_instrument
from .option_views import OPTION_FORMAT, find_option_instrument
from .utilities import mattermost_text
from .exceptions import BadRequestException
import re

def portfolios(request):
    if request.method == 'POST':
        body = request.POST.get('text', None)
        if len(body.split()) > 1:
            return create_portfolio(request)
        else:
            return get_portfolio(request)

    elif request.method == 'GET':
        return get_portfolio(request)

def get_portfolio(request):
    usage_str = "Usage: command-name portfolio_symbol"

    user_id = request.POST.get('user_id', None)
    user_name = request.POST.get('user_name', None)
    user = get_or_create_user(user_id, user_name)

    portfolio_symbol = request.POST.get('text', None)
    if not portfolio_symbol:
        raise BadRequestException(usage_str)

    try:
        portfolio = Portfolio.objects.get(symbol=portfolio_symbol)
    except Portfolio.DoesNotExist:
        return mattermost_text("Portfolio '{}' not found".format(portfolio_symbol))
    #securities = portfolio.security_set.all()
    securities = Security.objects.filter(portfolio=portfolio)

    response = "{}:\n{}".format(portfolio_symbol, securities_to_str(securities))
    return mattermost_text(response)

def create_portfolio(request):
    usage_str = "Usage: command-name portfolio_symbol STOCK1=NUM_STOCKS [STOCK2=NUM_STOCKS OPTION1=NUM_CONTRACTS...]"

    user_id = request.POST.get('user_id', None)
    user_name = request.POST.get('user_name', None)
    user = get_or_create_user(user_id, user_name)

    body = request.POST.get('text', None)
    if not body:
        raise BadRequestException(usage_str)
    parts = body.split(' ')
    if len(parts) < 2:
        raise BadRequestException(usage_str)

    portfolio_symbol = parts[0].upper()
    security_definitions = parts[1:]

    portfolio = get_or_create_portfolio(portfolio_symbol, user)

    # Get existing securities if portfolio already exists
    existing_securities = {}
    for security in portfolio.security_set.all():
        existing_securities[security.name] = security
    securities_to_delete = []
    new_securities = []

    for security_definition in security_definitions:
        invalid_security_str = "Invalid security definition: '{}'. Format must be [security_name]=[count]".format(security_definition)
        parts = re.split('[=:]', security_definition)
        if len(parts) != 2:
            raise BadRequestException(invalid_security_str)

        security_name = parts[0].upper()
        try:
            count = float(parts[1])
        except ValueError:
            raise BadRequestException(invalid_security_str)

        if count <= 0:
            raise BadRequestException("Invalid security count for {}: '{}'".format(security_name, count))

        # Find a matching security if one exists
        if security_name in existing_securities:
            security = existing_securities[security_name]
            del existing_securities[security_name]
        else:
            security = create_security(security_name, portfolio)

        security.count = count
        new_securities.append(security)
    # Save entries to database after all have been validated
    user.save()
    portfolio.save()
    [security.save() for security in new_securities]
    # Consider any securities not provided in this call as removed
    [security.delete() for security in existing_securities.values()]

    securities = Security.objects.filter(portfolio=portfolio)

    response = "Created your portfolio '{}':\n{}".format(portfolio_symbol, securities_to_str(new_securities))
    return mattermost_text(response)


def securities_to_str(securities):
    security_strs = []
    for s in securities:
        security_str = s.name + ' ' + ': '
        if s.count % 1 == 0:
            security_str += str(round(s.count))
        else:
            security_str += str(s.count)
        security_strs.append(security_str)
    return "\n".join(security_strs)

def create_security(security_name, portfolio):
    if re.match(SYMBOL_FORMAT, security_name):
        instrument = find_stock_instrument(security_name)
        type = Security.STOCK
    elif re.match(OPTION_FORMAT, security_name):
        instrument = find_option_instrument(security_name)
        type = Security.OPTION
    else:
        raise BadRequestException("'{}' does not match any known stock format (e.g. AMZN) or option format (e.g. MU90C@12-21)")

    return Security(name=security_name, portfolio=portfolio, type=type, instrument_id=instrument.id)

def get_or_create_user(user_id, user_name = None):
    if not user_id:
        raise BadRequestException("user_id is not present")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        if not user_name:
            raise BadRequestException("user_name is not present")
        user = User(id=user_id, name=user_name)
    return user

def get_or_create_portfolio(symbol, user):
    try:
        portfolio = Portfolio.objects.get(symbol=symbol)
        if portfolio.user.id != user.id:
            raise BadRequestException("{} already exists and belongs to {}, not you".format(symbol, user.name))
    except Portfolio.DoesNotExist:
        portfolio = Portfolio(symbol=symbol, user=user)
    return portfolio
