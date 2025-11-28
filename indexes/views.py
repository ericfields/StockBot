from .models import User, Index, Asset
from helpers.utilities import mattermost_text, mattermost_table
from quotes.aggregator import Aggregator
from exceptions import BadRequestException
from robinhood.models import Stock
import re
from django.db import connection

import logging

DATABASE_PRESENT = bool(connection.settings_dict['NAME'])

GENERAL_USAGE_STR = """Available commands:
/index create [index_name] [assets...]
/index rename [index_name]
/index add [index_name] [assets...]
/index remove [index_name] [assets...]
/index destroy [index_name]
"""

INDEX_COMMANDS = [
    'create',
    'rename',
    'destroy',
    'add',
    'remove'
]

INDEX_NAME_PATTERN = '^[A-Za-z]{1,14}$'

logger = logging.getLogger('stockbot')

def index(request):
    if not DATABASE_PRESENT:
        raise BadRequestException("No indexes database has been configured for this StockBot instance.")

    request_text = request.POST.get('text', None)
    if request_text and request_text.strip():
        return index_action(request)
    else:
        return display_index(request)

def index_action(request):
    body = request.POST.get('text', None)
    parts = re.split('[,\s]+', body)
    # Remove empty parts
    parts = [p for p in parts if p.strip()]
    if not parts:
        return display_index(request, None)

    command = parts[0]
    parts.pop(0)

    should_remove = False

    user = get_or_create_user(request)

    if command.lower() not in INDEX_COMMANDS:
        if re.match(INDEX_NAME_PATTERN, command):
            try:
                return display_index(request, command)
            except BadRequestException:
                raise BadRequestException(f"Unknown command or index: '{command}'\n{GENERAL_USAGE_STR}")
        else:
            raise BadRequestException(GENERAL_USAGE_STR)

    command = command.lower()

    if command == 'create':
        return create_index(user, parts)

    user_indexes = Index.objects.filter(user=user)

    if len(user_indexes) == 0:
        raise BadRequestException(f"You do not have any indexes. You must create an index to use the {command} command.")

    if len(user_indexes) == 1:
        index = user_indexes[0]
        if parts and parts[0].upper() == index.name:
            # The index name was provided unnecessarily, simply ignore it
            parts.pop(0)
    elif is_valid_index_name(parts[0]):
        try:
            index = next(i for i in user_indexes if i.name == parts[0].upper())
        except StopIteration:
            raise BadRequestException(f"You do not have an index named '{parts[0].upper()}'")
        parts.pop(0)
    else:
        return mattermost_text("You have multiple indexes. You must specify the index you want to modify.\n\t"        + "\n\t".join([p.name for p in user_indexes]))

    if command == 'rename':
        return rename_index(user, index, parts[0].upper())

    if command == 'destroy':
        if parts and parts[0].upper() != index.name:
            raise BadRequestException(f"You do not have an index named '{parts[0].upper()}'")
        return delete_index(index)

    if command == 'remove':
        should_remove = True

    if not parts:
        # This is an add/remove command, but no parts have been specified
        usage_str = ("Usage: /index {0} [asset1] [asset2]..."
        + "\nExamples:"
        + "\n\t/index {0} AAPL ({0} a single share of AAPL)"
        + "\n\t/index {0} MSFT:5 ({0} five shares of MSFT)"
        + "\n\t/index {0} AAPL:2 MSFT:3 ({0} two shares of AAPl and three shares of MSFT)"
        + "\n\t/index {0} AMZN$2000C@7/20 ({0} AMZN $2000 call option expiring July 20)"
        + "\n\t/index {0} AAPL180P8-31-20 ({0} AAPL $180 put option expiring August 31, 2020)"
        + "\n\t/index {0} MSFT200C ({0} MSFT $200 put option expiring end of this week)"
        + "\n\t/index {0} MSFT200.5C:10 ({0} ten MSFT $200.50 put options expiring end of this week)"
        )

        raise BadRequestException(usage_str.format(command))

    return update_index(index, parts, should_remove=should_remove)

def display_index(request, index_name=None):
    user = get_or_create_user(request)
    index = None

    if index_name:
        try:
            index = Index.objects.get(name=index_name.upper())
        except Index.DoesNotExist:
            raise BadRequestException("Index does not exist: '{}'".format(index_name))
    else:
        indexes = Index.objects.filter(user=user)
        if not indexes:
            return mattermost_text("You do not have any indexes.\n\t" +
                "\n\t".join([p.name for p in indexes])
            )
        elif len(indexes) == 1:
            index = indexes[0]
        else:
            return mattermost_text("You have multiple indexes. Specify the index you want to view.\n\t" +
                "\n\t".join([p.name for p in indexes])
            )

    aggregator = Aggregator(index)

    return print_index(index, aggregator, index.user == user)

def rename_index(user: User, index: str, new_index_name: str):
    validate_index_name(new_index_name)

    try:
        existing_index = Index.objects.get(name=new_index_name)
        if existing_index.user_id == user.id:
            raise BadRequestException("You already have an index named {}".format(new_index_name))
        else:
            raise BadRequestException("{} already exists and belongs to {}".format(new_index_name, existing_index.user.name))
    except Index.DoesNotExist:
        pass

    index.name = new_index_name
    index.save()

    return mattermost_text("Index renamed to {}".format(new_index_name))

def create_index(user, parts):
    usage_str = "Usage: /index create [name] [stock1:count, [stock2: count, [option1: count...]]]"

    if not parts:
        raise BadRequestException(usage_str)

    # Check for index name
    name = parts[0].upper()
    validate_index_name(name)

    index = None

    # Verify that this index name isn't already taken by someone else
    try:
        index = Index.objects.get(name=name)
        if index.user_id != user.id:
            raise BadRequestException("{} belongs to {}".format(name, index.user.name))
    except Index.DoesNotExist:
        pass

    if index:
        # Delete the index so that it can be recreated again
        index.delete()

    index = Index.objects.create(user=user, name=name)

    parts.pop(0)

    return update_index(index, parts)

def delete_index(index):
    index.delete()
    return mattermost_text("{} deleted.".format(index.name))

def update_index(index, asset_defs, **opts):
    aggregator = Aggregator()
    process_assets(index, aggregator, asset_defs, **opts)

    return print_index(index, aggregator)

def process_assets(index, aggregator, asset_defs, should_remove = False):
    assets_to_save = []
    identifier_count_map = {}
    for ad in asset_defs:
        parts = re.split('[:=]', ad)
        if not parts:
            raise BadRequestException("Invalid definition: '{}'".format(ad))

        identifier = parts[0].upper()

        if len(parts) > 1:
            try:
                count = float(parts[1])
                if count > 1000000000:
                    raise BadRequestException("Cannot track more than one billion shares of an asset.")
            except ValueError:
                raise BadRequestException("Invalid count: '{}'".format(parts[1]))
        else:
            # If adding an asset, assume a default count of 1
            # If removing, assume all shares/contracts of the asset are being removed
            if should_remove:
                count = None
            else:
                count = 1

        identifier_count_map[identifier] = count

    # Load all existing instruments, as well as the ones we are adding/removing
    aggregator.load_instruments(index, *identifier_count_map.keys())

    for identifier in identifier_count_map:
        instrument = aggregator.get_instrument(identifier)
        count = identifier_count_map[identifier]
        if should_remove:
            remove_assets(index, instrument, count)
        else:
            add_assets(index, instrument, count)

    index.save()


def add_assets(index, instrument, count):
    try:
        asset = index.asset_set.get(instrument_id=instrument.id)
        asset.count += count
    except Asset.DoesNotExist:
        asset = index.asset_set.create(instrument=instrument, count=count)

    asset.save()

def remove_assets(index, instrument, count):
    try:
        asset = index.asset_set.get(instrument_id=instrument.id)
    except Asset.DoesNotExist:
        raise BadRequestException("You do not have any {} in your index".format(instrument))

    if not count:
        # Assume the user wants to remove all shares from the index
        count = asset.count
    elif count > asset.count:
        raise BadRequestException("You do not have {} {} {}(s) to remove in your index".format(
            count, instrument, instrument.__class__.__name__.lower()
        ))

    asset.count -= count
    if asset.count == 0:
        asset.delete()
    else:
        asset.save()


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

def is_valid_index_name(name):
    try:
        validate_index_name(name)
        return True
    except BadRequestException:
        return False

def validate_index_name(name):
    name = name.upper()
    if not re.match(INDEX_NAME_PATTERN, name):
        raise BadRequestException("Invalid name: '{}'. Symbol must be an alphabetic string no longer than 14 characters.".format(name))
    if name == 'EVERYONE':
        raise BadRequestException("'EVERYONE' is a reserved keyword. You must choose a different name for your index.")
    # Verify that this index name does not match a stock name
    if Stock.search(symbol=name):
        raise BadRequestException("Can't use this name; a stock named {} already exists".format(name))


def print_index(index, aggregator, is_owner=True):
    quotes = aggregator.quotes()

    assets = index.asset_set.all()
    for a in assets:
        a.instrument_object = aggregator.get_instrument(a.identifier)
    total_value = sum([asset_value(quotes, a) for a in assets])

    asset_str = assets_table(assets, quotes, total_value, is_owner)

    index_str = index.name
    if is_owner:
        index_str += " (${:,.2f}):".format(total_value)
    index_str += "\n\n{}".format(asset_str)

    return mattermost_text(index_str)

def asset_value(quotes, asset, count=None):
    if not count:
        count = asset.count
    if asset.instrument_url in quotes:
        return quotes[asset.instrument_url].price() * count * asset.unit_count()
    else:
        return 0

def assets_table(assets, quotes, total_value, is_owner):
    if not assets:
        return "No assets in index"

    table_rows = []
    if is_owner:
        table_rows.append([ 'Asset', 'Change', 'Count', 'Value', '% of Index' ])
    else:
        table_rows.append([ 'Asset', 'Change', '% of Index'])

    assets: list[Asset] = sorted(assets, reverse=True, key=lambda a: change_impact(a, quotes))

    for a in assets:
        row_asset = a.identifier
        row_percent_of_index = '0%'
        row_change = '0%'

        if a.instrument_url in quotes:
            value = asset_value(quotes, a)

            quote = quotes[a.instrument_url]
            previous_close_price = quote.previous_close if a.type == Asset.STOCK else quote.previous_close_price
            change = (quote.price() - previous_close_price) / previous_close_price * 100
            row_change = str(round(change, 2)) + '%'
            if change > 0:
                row_change = '+' + row_change
        else:
            value = 0
            if a.expired():
                row_asset += ' (expired)'
            else:
                row_asset += ' (delisted)'

        row_value = '$' + str(round(value, 2))

        if total_value > 0:
            row_percent_of_index = str(round(value / total_value * 100, 2)) + '%'

        if is_owner:
            if a.count % 1 == 0:
                row_count = str(round(a.count))
            else:
                row_count = str(a.count)

            table_rows.append([row_asset, row_change, row_count, row_value, row_percent_of_index])
        else:
            table_rows.append([row_asset, row_change, row_percent_of_index])

    return mattermost_table(table_rows)

def change_impact(asset, quotes):
    if asset.instrument_url not in quotes:
        return 0

    quote = quotes[asset.instrument_url]
    previous_close_price = quote.previous_close if asset.type == Asset.STOCK else quote.previous_close_price
    value_change = (quote.price() - previous_close_price) * asset.count * asset.unit_count()
    return abs(value_change)
