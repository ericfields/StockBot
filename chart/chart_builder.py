from datetime import datetime, timedelta
import re

from django.db import connection
from chart.chart import Chart
from chart.chart_data import ChartData
from helpers.utilities import str_to_duration
from indexes.models import Asset, Index

from quotes.aggregator import Aggregator
from exceptions import BadRequestException
from robinhood.models import Market

MARKET = 'XNYS'

DATABASE_PRESENT = bool(connection.settings_dict['NAME'])

def build_chart(identifiers, span = 'day'):
    span = str_to_duration(span)

    aggregator = Aggregator()
    indexes, title = get_indexes_and_title(aggregator, identifiers)

    # Hide the pricing information for a user index
    hide_value = any([p.pk for p in indexes])

    chart_data_sets: list[ChartData] = []
    for index in indexes:
        # If this is a chart for a singular user index, plot each asset on its own line
        if index.pk and len(indexes) == 1:
            for asset in index.assets():
                chart_data_sets.append(ChartData(asset.identifier, asset.identifier, [asset]))
        else:
            chart_data_sets.append(ChartData(index.name, index.identifier, index.assets()))

    # Show the price only when quoting a single asset not from a user index
    show_price = len(chart_data_sets) == 1 and not indexes[0].pk

    market = Market.get(MARKET)
    market_hours = market.hours()
    if not (market_hours.is_open and datetime.now() >= market_hours.extended_opens_at):
        # Get the most recent open market hours, and change the start/end time accordingly
        market_hours = market_hours.previous_open_hours()

    start_time, end_time = get_start_and_end_time(market_hours, span)

    quotes, historicals = aggregator.quotes_and_historicals(start_time, end_time)

    for chart_data in chart_data_sets:
        chart_data.load(quotes, historicals, start_time, end_time)

    chart = Chart(title, span, market.timezone, market_hours, hide_value)
    chart.plot(*chart_data_sets, show_price=show_price)
    return chart

def get_indexes_and_title(aggregator: Aggregator, identifiers: set[str]) -> tuple[list[Index], str]:
    # Remove duplicates by converting to set (and back)
    identifiers = set(identifiers.upper().split(','))
    if len(identifiers) > 10:
        raise BadRequestException("Sorry, you can only quote up to ten stocks/indexes at a time.")

    indexes = []
    title = None

    if DATABASE_PRESENT:
        # Determine which identifiers, if any, are indexes
        if 'EVERYONE' in identifiers:
            for index in Index.objects.all():
                indexes.append(index)
                identifiers.discard(index.name)
            identifiers.discard('EVERYONE')
        else:
            for identifier in list(identifiers):
                index = find_index(identifier)
                if index:
                    indexes.append(index)
                    identifiers.discard(identifier)

    # Load instruments for all index assets and identifiers
    aggregator.load_instruments(*indexes, *identifiers)

    # Wrap each of the remaining non-index instruments in its own index
    for identifier in identifiers:
        instrument = aggregator.get_instrument(identifier)
        index = Index(name=instrument.full_name(), identifier=instrument.identifier())
        asset = Asset(index=index, instrument=instrument, count=1)
        index.add_asset(asset)
        indexes.append(index)

    if not title:
        title = ', '.join([p.name for p in indexes])

    return indexes, title

def find_index(name) -> Index:
    if not re.match('^[A-Z]{1,14}$', name):
        return None

    try:
        return Index.objects.get(name=name)
    except Index.DoesNotExist:
        return None

def get_start_and_end_time(market_hours, span):
    now = datetime.now()

    end_time = market_hours.extended_closes_at
    if now < end_time:
        end_time = now
    if span <= timedelta(days=1):
        start_time = market_hours.extended_opens_at
    else:
        start_time = end_time - span
    return start_time, end_time