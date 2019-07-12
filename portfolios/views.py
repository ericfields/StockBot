from .models import User, Portfolio, Asset
from helpers.utilities import mattermost_text, find_instrument
from quotes.aggregator import quote_aggregate
from exceptions import BadRequestException
from robinhood.models import Stock, Option
from datetime import datetime
import re
from django.db import connection

import logging

DATABASE_PRESENT = bool(connection.settings_dict['NAME'])

GENERAL_USAGE_STR = """Available commands:
/portfolio create [portfolio_name] [$cash] [assets...]
/portfolio rename [portfolio_name]
/portfolio add [portfolio_name] [$cash] [assets...]
/portfolio remove [portfolio_name] [$cash] [assets...]
/portfolio buy [portfolio_name] [assets...]
/portfolio sell [portfolio_name] [assets...]
/portfolio destroy [portfolio_name]
/portfolio visibility [portfolio_name] private|listings|ratios|shares|public
"""

VISIBILITY_USAGE_STR = """Usage: /portfolio visibility [portfolio_name] private|listings|ratios|shares|public
    private: Only you can see any details about your portfolio.
    listings: Other uses can see what stocks/options you are holding, but not how many.
    ratios: Other uses can see relative amounts of stocks/options you are holding, as percentages of your portfolio's total value.
    shares: Other users can see what stocks/options you are holding and how many. They cannot see how much cash is present, or your portfolio's total value.
    public: Other users can see all details of your portfolio, including assets, amounts, cash, and total value.
"""

PORTFOLIO_COMMANDS = [
    'create',
    'rename',
    'destroy',
    'add',
    'remove',
    'buy',
    'sell',
    'visibility'
]

logger = logging.getLogger('stockbot')

def portfolio(request):
    if not DATABASE_PRESENT:
        raise BadRequestException("No portfolios database has been configured for this StockBot instance.")

    if request.POST.get('text', None):
        return portfolio_action(request)
    else:
        return display_portfolio(request)

def portfolio_action(request):
    body = request.POST.get('text', None)
    parts = re.split('[,\s]+', body)
    # Remove empty parts
    parts = list(filter(None, parts))

    command = parts[0]
    parts.pop(0)

    remove_assets = False
    maintain_value = False

    user = get_or_create_user(request)

    if command.lower() not in PORTFOLIO_COMMANDS:
        if re.match('^[A-Z]{1,14}$', command):
            return display_portfolio(request, command)
        else:
            raise BadRequestException(GENERAL_USAGE_STR)

    command = command.lower()

    if command == 'create':
        return create_portfolio(user, parts)

    if parts and re.match('^[A-Z]{1,14}$', parts[0]):
        portfolio_name = parts[0]
    else:
        portfolio_name = None
    portfolio = find_portfolio(user, portfolio_name)
    if portfolio_name and portfolio.name == portfolio_name:
        parts.pop(0)

    if command == 'rename':
        return rename_portfolio(portfolio, parts)

    if command == 'destroy':
        return delete_portfolio(portfolio)

    if command == 'visibility':
        if not parts or len(parts) > 1:
            raise BadRequestException(VISIBILITY_USAGE_STR)
        return toggle_portfolio_visibility(portfolio, parts[0])

    remove_assets = False
    maintain_value = False

    if command == 'remove':
        remove_assets = True
    elif command == 'buy':
        maintain_value = True
    elif command == 'sell':
        maintain_value = True
        remove_assets = True

    if not parts:
        # This is an add/remove/buy/sell command, but no parts have been specified
        usage_str = ("Usage: /portfolio {0} [asset1] [asset2]..."
        + "\nExamples:"
        + "\n\t/portfolio {0} AAPL ({0} a single share of AAPL)"
        + "\n\t/portfolio {0} MSFT:5 ({0} five shares of MSFT)"
        + "\n\t/portfolio {0} AAPL:2 MSFT:3 ({0} two shares of AAPl and three shares of MSFT)"
        + "\n\t/portfolio {0} AMZN$2000C@7/20 ({0} AMZN $2000 call option expiring July 20)"
        + "\n\t/portfolio {0} AAPL180P8-31-20 ({0} AAPL $180 put option expiring August 31, 2020)"
        + "\n\t/portfolio {0} MSFT200C ({0} MSFT put option expiring end of this week"
        + "\n\t/portfolio {0} MSFT200C:10 ({0} ten MSFT put options expiring end of this week"
        )
        if not maintain_value:
            usage_str += "\n\t/portfolio {0} $100 ({0} $100 in cash)"

        raise BadRequestException(usage_str.format(command))

    return update_portfolio(portfolio, parts, remove_assets=remove_assets, maintain_value=maintain_value)

def toggle_portfolio_visibility(portfolio, visibility):
    if visibility == 'private':
        portfolio.visibility = Portfolio.Visibility.PRIVATE
        result_str = "All contents of the portfolio are now hidden from other users."
    elif visibility == 'listings':
        portfolio.visibility = Portfolio.Visibility.LISTINGS
        result_str = "Other users can now see the stocks/options in the portfolio (but not their amounts)."
    elif visibility == 'ratios':
        portfolio.visibility = Portfolio.Visibility.RATIOS
        result_str = "Other users can now see the stocks/options in the portfolio, and the percentage of the total portfolio value that each stock/option consists of."
    elif visibility == 'shares':
        portfolio.visibility = Portfolio.Visibility.SHARES
        result_str = "Other users can now see the actual amounts of each stocks/option you have in the portfolio."
    elif visibility == 'public':
        portfolio.visibility = Portfolio.Visibility.PUBLIC
        result_str = "Other users can now see the full contents and monetary value of the portfolio, including cash amounts."
    else:
        raise BadRequestException("Invalid visibility level: {}\n{}".format(visibility, VISIBILITY_USAGE_STR))

    portfolio.save()

    return mattermost_text("The visibility of portfolio {} is now set to '{}'. {}".format(
        portfolio.name, portfolio.visibility.name.lower(), result_str
    ))

def display_portfolio(request, portfolio_name=None):
    user = get_or_create_user(request)
    portfolio = None

    if portfolio_name:
        try:
            portfolio = Portfolio.objects.get(name=portfolio_name)
            if portfolio.user != user and portfolio.visibility == Portfolio.Visibility.PRIVATE:
                raise BadRequestException("This portfolio is set to private, and you do not own it. You cannot see its contents.")
        except Portfolio.DoesNotExist:
            raise BadRequestException("Portfolio does not exist: '{}'".format(portfolio_name))
    else:
        portfolios = Portfolio.objects.filter(user=user)
        if not portfolios:
            return mattermost_text("You do not have any portfolios.\n\t" +
                "\n\t".join([p.name for p in portfolios])
            )
        elif len(portfolios) == 1:
            portfolio = portfolios[0]
        else:
            return mattermost_text("You have multiple portfolios. Specify the portfolio you want to view.\n\t" +
                "\n\t".join([p.name for p in portfolios])
            )

    return print_portfolio(portfolio, portfolio.user == user)

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

def find_portfolio(user, portfolio_name=None):
    if portfolio_name:
        try:
            portfolio = Portfolio.objects.get(name=portfolio_name)
            if portfolio.user != user:
                raise BadRequestException("You do not own this portfolio.")
            return portfolio
        except Portfolio.DoesNotExist:
            # Provided field may not actually be a portfolio name, but an instrument.
            # If so, simply use the user's one and only portfolio if they have one.
            # If not, raise an error.
            try:
                get_instrument(portfolio_name)
            except BadRequestException:
                raise BadRequestException("No such portfolio or stock/option exists: '{}'".format(portfolio_name))

    portfolios = Portfolio.objects.filter(user=user)
    if not portfolios:
        raise BadRequestException("You do not have a portfolio")
    elif len(portfolios) == 1:
        portfolio = portfolios[0]
    else:
        raise BadRequestException("You have multiple portfolios. Specify the portfolio you want to interact with.\n\t" +
            "\n\t".join([p.name for p in portfolios])
        )
    return portfolio

def get_instrument(identifier):
    # Check if an instrument URL exists in the portfolio database first
    try:
        return Asset.objects.get(identifier=identifier).instrument()
    except Asset.DoesNotExist:
        return find_instrument(identifier)

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
            # If buying an asset, assume a default count of 1
            # If selling, assume all shares/contracts are being sold
            if remove_assets:
                count = None
            else:
                count = 1

        instrument = get_instrument(identifier)
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

    if not count:
        # Assume the user wants to sell all their shares
        count = asset.count
    elif count > asset.count:
        raise BadRequestException("You do not have {} {} {}(s) to sell in your portfolio".format(
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


def print_portfolio(portfolio, is_owner=True):
    if is_owner:
        visibility = Portfolio.Visibility.PUBLIC
    else:
        visibility = portfolio.visibility

    quotes = quote_aggregate(portfolio)

    assets = portfolio.asset_set.all()
    cash_value = portfolio.cash
    total_value = sum([asset_value(quotes, a) for a in assets]) + cash_value

    asset_str = assets_to_str(assets, quotes, total_value, visibility)

    portfolio_str = portfolio.name
    if visibility == Portfolio.Visibility.PUBLIC:
        portfolio_str += " (${:,.2f}):\n\tCash: ${:,.2f}".format(total_value, cash_value)
    portfolio_str += "\n\t{}".format(asset_str)

    return mattermost_text(portfolio_str)

def asset_value(quotes, asset, count=None):
    if not count:
        count = asset.count
    instrument_id = str(asset.instrument_id)
    if instrument_id in quotes:
        return quotes[instrument_id].price() * count * asset.unit_count()
    else:
        return 0

def assets_to_str(assets, quotes, total_value, visibility):
    asset_strs = []
    for a in assets:
        asset_str = a.identifier
        if str(a.instrument_id) not in quotes:
            asset_str += " (delisted)"
            asset_strs.append(asset_str)
            continue

        if visibility > Portfolio.Visibility.LISTINGS:
            asset_str += ": "
            if a.count % 1 == 0:
                real_amount = round(a.count)
            else:
                real_amount = a.count

            real_value = asset_value(quotes, a)
            proportion = real_value / total_value

            if visibility == Portfolio.Visibility.RATIOS:
                asset_str += "{:.2f}%".format(proportion * 100)
            elif visibility >= Portfolio.Visibility.SHARES:
                asset_str += "{} (${:.2f}, {:.2f}%)".format(real_amount, real_value, proportion * 100)
        asset_strs.append(asset_str)
    if not asset_strs:
        return "No assets in portfolio"
    return "\n\t".join(asset_strs)
