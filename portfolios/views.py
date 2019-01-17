from .models import User, Portfolio, Asset
from helpers.utilities import mattermost_text, find_instrument
from quotes.aggregator import quote_aggregate
from exceptions import BadRequestException
from robinhood.models import Stock, Option
from datetime import datetime
import re

def portfolio(request):
    if request.POST.get('text', None):
        return portfolio_action(request)
    else:
        return display_portfolio(request)

def portfolio_action(request):
    usage_str = """Usage:
/portfolio create [name] [$cash] [stock1:count, [stock2: count, [option1: count...]]]
/portfolio rename [name]
/portfolio add [$cash] [stock1:count, [stock2: count, [option1: count...]]]
/portfolio remove [$cash] [stock1:count, [stock2: count, [option1: count...]]]
/portfolio buy [stock1:count, [stock2: count, [option1: count...]]]
/portfolio sell [stock1:count, [stock2: count, [option1: count...]]]
/portfolio destroy
"""

    body = request.POST.get('text', None)
    parts = re.split('[,\s]+', body)
    # Remove empty parts
    parts = list(filter(None, parts))

    command = parts[0]
    parts.pop(0)

    remove_assets = False
    maintain_value = False

    user = get_or_create_user(request)

    if command.lower() not in ['create', 'rename', 'destroy', 'add', 'remove', 'buy', 'sell']:
        if re.match('^[A-Z]{1,14}$', command):
            return display_portfolio(request, command)
        else:
            raise BadRequestException(usage_str)

    command = command.lower()

    if command == 'create':
        return create_portfolio(user, parts)

    portfolio_name = None
    if parts:
        portfolio_name = parts.pop(0)
    portfolio = get_portfolio(user, portfolio_name)

    if command == 'rename':
        return rename_portfolio(portfolio, parts)

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

def display_portfolio(request, portfolio_name=None):
    user = get_or_create_user(request)
    portfolio = None

    if portfolio_name:
        try:
            portfolio = Portfolio.objects.get(name=portfolio_name)
            if portfolio.user != user:
                raise BadRequestException("You do not own this portfolio.")
        except Portfolio.DoesNotExist:
            raise BadRequestException("Portfolio does not exist: '{}'".format(portfolio_name))
    else:
        portfolios = Portfolio.objects.filter(user=user)
        if len(portfolios) == 1:
            portfolio = portfolios[0]
        else:
            return mattermost_text("You have multiple portfolios. Specify the portfolio you want to view.\n\t" +
                "\n\t".join([p.name for p in portfolios])
            )

    return print_portfolio(portfolio)

def rename_portfolio(portfolio, parts):
    if not parts:
        raise BadRequestException("Usage: /portfolio rename [newname]")

    # Check portfolio name
    name = parts[0].upper()
    verify_name(name)

    try:
        existing_portfolio = Portfolio.objects.get(name=name)
        if existing_portfolio.user_id == user.id:
            raise BadRequestException("Your portfolio is already named {}".format(name))
        else:
            raise BadRequestException("{} already exists and belongs to {}".format(name, existing_portfolio.user.name))
    except Portfolio.DoesNotExist:
        # Rename the user's current portfolio name
        pass

    portfolio.name = name
    portfolio.save()

    return mattermost_text("Portfolio renamed to {}".format(name))

def get_portfolio(user, portfolio_name=None):
    if portfolio_name:
        try:
            portfolio = Portfolio.objects.get(name=portfolio_name)
            if portfolio.user != user:
                raise BadRequestException("You do not own this portfolio.")
        except Portfolio.DoesNotExist:
            raise BadRequestException("Portfolio does not exist: '{}'".format(portfolio_name))
    else:
        portfolios = Portfolio.objects.filter(user=user)
        if not portfolios:
            raise BadRequestException("You do not have a portfolio")
        elif len(portfolios) == 1:
            portfolio = portfolios[0]
        else:
            raise BadRequestException("You have multiple portfolios. Specify the portfolio you want to interact with.\n\t" +
                "\n\t".join([p.name for p in portfolios])
            )

def create_portfolio(user, parts):
    usage_str = "Usage: /portfolio create [name] [$cash] [stock1:count, [stock2: count, [option1: count...]]]"

    if not parts:
        raise BadRequestException(usage_str)

    # Check for portfolio name
    name = parts[0].upper()
    verify_name(name)

    portfolio = None

    # Verify that this portfolio name isn't already taken by someone else
    try:
        portfolio = Portfolio.objects.get(name=name)
        if portfolio.user_id != user.id:
            raise BadRequestException("{} belongs to {}".format(name, portfolio.user.name))
    except Portfolio.DoesNotExist:
        pass

    if portfolio:
        # Delete the portfolio so that it can be recreated again
        portfolio.delete()

    portfolio = Portfolio.objects.create(user=user, name=name)

    parts.pop(0)

    return update_portfolio(portfolio, parts)

def delete_portfolio(portfolio):
    portfolio.delete()
    return mattermost_text("{} deleted.".format(portfolio.name))

def update_portfolio(portfolio, asset_defs, **opts):
    process_assets(portfolio, asset_defs, **opts)

    return print_portfolio(portfolio)

def process_assets(portfolio, asset_defs, remove_assets = False, maintain_value = False):
    assets_to_save = []
    instrument_counts = []
    for ad in asset_defs:
        # Check for cash value
        if re.match('^\$[0-9]+(\.[0-9]{2})?$', ad):
            if maintain_value:
                raise BadRequestException("You cannot buy/sell cash, only stocks and options")
            cash_value = float(ad.replace('$', ''))
            if cash_value > 1000000000:
                raise BadRequestException("Highly doubt you have over a billion dollars in cash")
            elif remove_assets:
                if cash_value > portfolio.cash:
                    raise BadRequestException("You do not have {} in cash to remove".format(ad))
                portfolio.cash -= cash_value
            else:
                portfolio.cash += cash_value
            continue

        parts = re.split('[:=]', ad)
        if not parts:
            raise BadRequestException("Invalid definition: '{}'".format(ad))

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

        instrument = find_instrument(identifier)
        instrument_counts.append((instrument,count))

    instruments = [ic[0] for ic in instrument_counts]
    quotes = quote_aggregate(*instruments)

    for instrument_count in instrument_counts:
        instrument, count = instrument_count
        if remove_assets:
            value_sold = sell_assets(portfolio, instrument, count, quotes)
            if maintain_value:
                portfolio.cash += value_sold
        else:
            value_bought = buy_assets(portfolio, instrument, count, quotes)
            if maintain_value:
                if portfolio.cash < value_bought:
                    raise BadRequestException("You do not have enough cash in your portfolio to buy these assets.")
                portfolio.cash -= value_bought

    portfolio.save()


def buy_assets(portfolio, instrument, count, quotes):
    try:
        asset = portfolio.asset_set.get(instrument_id=instrument.id)
        asset.count += count
    except Asset.DoesNotExist:
        asset = portfolio.asset_set.create(instrument=instrument, count=count)

    asset.save()

    return asset_value(quotes, asset, count)

def sell_assets(portfolio, instrument, count, quotes):
    try:
        asset = portfolio.asset_set.get(instrument_id=instrument.id)
    except Asset.DoesNotExist:
        raise BadRequestException("You do not have any {} in your portfolio".format(instrument))

    if count > asset.count:
        raise BadRequestException("You do not have {} {} {}s to sell in your portfolio".format(
            count, instrument, instrument.__class__.__name__.lower()
        ))

    asset.count -= count
    value_sold = asset_value(quotes, asset, count)
    if asset.count == 0:
        asset.delete()
    else:
        asset.save()

    return value_sold

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

def verify_name(name):
    name = name.upper()
    if not re.match('^[A-Z]{1,14}$', name):
        raise BadRequestException("Invalid name: '{}'. Symbol must be an alphabetic string no longer than 14 characters.".format(name))
    if name == 'EVERYONE':
        raise BadRequestException("'EVERYONE' is a reserved keyword. You must choose a different name for your portfolio.")
    # Verify that this portfolio name does not match a stock name
    if Stock.search(symbol=name):
        raise BadRequestException("Can't use this name; a stock named {} already exists".format(name))
    return True


def print_portfolio(portfolio):
    quotes = quote_aggregate(portfolio)

    assets = portfolio.asset_set.all()
    cash_value = portfolio.cash
    total_value = sum([asset_value(quotes, a) for a in assets]) + cash_value
    response = "{} (${:,.2f}):\n\tCash: ${:,.2f}\n\t{}".format(
        portfolio.name, total_value, cash_value, assets_to_str(assets)
    )
    return mattermost_text(response)

def asset_value(quotes, asset, count=None):
    if not count:
        count = asset.count
    return quotes[str(asset.instrument_id)].price() * count

def assets_to_str(assets):
    asset_strs = []
    for a in assets:
        asset_str = a.identifier + ': '
        if a.count % 1 == 0:
            asset_str += str(round(a.count))
        else:
            asset_str += str(a.count)
        asset_strs.append(asset_str)
    if not asset_strs:
        return "No assets in portfolio"
    return "\n\t".join(asset_strs)
