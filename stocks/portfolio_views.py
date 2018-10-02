from .models import User, Portfolio, Asset
from .stock_handler import StockHandler
from .option_handler import OptionHandler
from .utilities import mattermost_text, find_instrument
from .exceptions import BadRequestException
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
        # Check for portfolio name
        if not parts:
            raise BadRequestException("Usage: /portfolio rename [name]")

        name = parts[0].upper()
        if verify_name(name):
            portfolio.name = name
            portfolio.save()
            return mattermost_text("Portfolio renamed to {}".format(name))
        else:
            raise BadRequestException("Invalid name: '{}'. Symbol must be an alphabetic string no longer than 14 characters.".format(name))

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
    usage_str = "Usage: /portfolio create [name] [$cash] [stock1:count, [stock2: count, [option1: count...]]]"

    if not parts:
        raise BadRequestException(usage_str)

    # Check for portfolio name
    if verify_name(parts[0]):
        name = parts[0].upper()
        portfolio = get_or_create_portfolio(user, name)
        parts.pop(0)
    else:
        # Get the user's existing portfolio, if present
        portfolio = get_or_create_portfolio(user)

    return update_portfolio(portfolio, parts, replace_assets=True)

def delete_portfolio(portfolio):
    portfolio.delete()
    return mattermost_text("{} deleted.".format(portfolio.name))

def update_portfolio(portfolio, asset_defs, **opts):
    process_assets(portfolio, asset_defs, **opts)

    return print_portfolio(portfolio)

def process_assets(portfolio, asset_defs, remove_assets = False, maintain_value = False, replace_assets = False):
    assets_to_save = []
    for ad in asset_defs:
        # Check for cash value
        if re.match('^\$[0-9]+(\.[0-9]{2})?$', ad):
            if maintain_value:
                raise BadRequestException("Cannot specify a cash value in buy/sell commands")
            cash_value = float(ad.replace('$', ''))
            if cash_value > 1000000000:
                raise BadRequestException("Highly doubt you have over a billion dollars in cash")
            if replace_assets:
                portfolio.cash = cash_value
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

        asset = get_or_create_asset(portfolio, identifier)

        if replace_assets:
            # Ensure the count starts at 0 since it's being replaced
            asset.count = 0

        cash_value = asset.instrument().current_value() * count

        if remove_assets:
            if count > asset.count:
                if count % 1 == 0:
                    count = round(count)
                type = asset.get_type_display()
                raise BadRequestException("You do not have {} {} {}(s) to sell in your portfolio".format(count, identifier, type))
            asset.count -= count
            if maintain_value:
                portfolio.cash += cash_value
        else:
            if maintain_value:
                if portfolio.cash < cash_value:
                    raise BadRequestException("You do not have enough cash to buy {} {} {}s. You must have at least ${:,.2f} in your portfolio to buy these (you currently have ${:,.2f}).".format(
                        count, identifier, asset.get_type_display(), cash_value, portfolio.cash
                    ))
                portfolio.cash -= cash_value

            asset.count += count

        assets_to_save.append(asset)

    # Wait until all transactions have been validated before modifying the database

    if replace_assets:
        # Delete any assets not specified in this request
        new_asset_ids = [a.id for a in assets_to_save]
        for a in portfolio.asset_set.all():
            if not a._state.adding and a.id not in new_asset_ids:
                a.delete()

    for a in assets_to_save:
        if a.count <= 0:
            a.delete()
        else:
            a.save()

    portfolio.save()


def get_or_create_asset(portfolio, identifier):
    instrument = find_instrument(identifier)
    try:
        return Asset.objects.get(portfolio=portfolio, instrument_id=instrument.id)
    except Asset.DoesNotExist:
        if isinstance(instrument, Stock):
            type = Asset.STOCK
        elif isinstance(instrument, Option):
            type = Asset.OPTION
        else:
            raise Exception("No Asset type defined for instrument of type '{}''".format(type(instrument)))

        return Asset(portfolio=portfolio, instrument_id=instrument.id,
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

def get_or_create_portfolio(user, name = None):
    portfolio = None
    if name: # We can create the portfolio if it does not exist
        try:
            portfolio = Portfolio.objects.get(name=name)
            if portfolio.user_id != user.id:
                raise BadRequestException("{} belongs to {}".format(name, portfolio.user.name))
        except Portfolio.DoesNotExist:
            # Replace the user's current portfolio name if it exists
            try:
                portfolio = Portfolio.objects.get(user=user)
            except Portfolio.DoesNotExist:
                portfolio = Portfolio(user=user)

            # Verify that this portfolio name does not match a stock name
            if Stock.search(symbol=name):
                raise BadRequestException("Can't use this name; a stock named {} already exists".format(name))

            portfolio.name = name
            portfolio.save()
    else:
        try:
            portfolio = Portfolio.objects.get(user=user)
        except Portfolio.DoesNotExist:
            raise BadRequestException("You don't have a portfolio.")
    return portfolio

def verify_name(name):
    name = name.upper()
    if re.match('^[A-Z]{1,14}$', name):
        return True
    else:
        return False


def print_portfolio(portfolio):
    assets = portfolio.asset_set.all()
    cash_value = portfolio.cash
    total_value = sum([a.current_value() for a in assets]) + cash_value
    response = "{} (${:,.2f}):\n\tCash: ${:,.2f}\n\t{}".format(
        portfolio.name, total_value, cash_value, assets_to_str(assets)
    )
    return mattermost_text(response)

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
