from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.urls import reverse
from django.http import HttpResponse

from indexes.models import Index, Asset
from robinhood.models import Stock, Market
from helpers.utilities import str_to_duration, mattermost_text
from chart.chart import Chart
from chart.chart_data import ChartData
from quotes.aggregator import Aggregator

from datetime import datetime, timedelta
import json
import re

from django.db import connection

from exceptions import BadRequestException

MARKET = 'XNYS'

DATABASE_PRESENT = bool(connection.settings_dict['NAME'])

def get_chart(request, identifiers, span = 'day'):
    span = str_to_duration(span)

    aggregator = Aggregator()
    indexes = get_indexes(aggregator, identifiers)

    # Hide the pricing information for a user index
    hide_value = any([p.pk for p in indexes])

    title = ', '.join([p.name for p in indexes])

    chart_data_sets = [ChartData(p) for p in indexes]
    indexes = [cd.index for cd in chart_data_sets]

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
    chart.plot(*chart_data_sets)

    chart_img_data = chart.get_img_data()
    return HttpResponse(chart_img_data, content_type="image/png")

def get_chart_img(request, img_name):
    if cache.has_key(img_name):
        return cache.get(img_name)

    parts = img_name.split("_")
    if len(parts) < 3:
        raise BadRequestException("Invalid image: '{}'".format(img_name))
    identifiers = parts[0]
    span = parts[-1]

    response = get_chart(request, identifiers, span)
    cache.set(img_name, response)
    return response


def get_mattermost_chart(request):
    body = request.POST.get('text', None)
    if not body:
        raise BadRequestException("No stocks/options/indexes specified")
    parts = body.split()
    identifiers = parts[0].upper()
    if len(parts) > 1:
        span = parts[1]
    else:
        span = 'day'

    chart_response = mattermost_chart(request, identifiers, span)
    return HttpResponse(json.dumps(chart_response), content_type="application/json")

def get_mattermost_chart_for_all(request):
    orig_text = request.POST.get('text', '').strip()
    new_text = 'EVERYONE'
    if orig_text:
        # Verify that text is a duration
        str_to_duration(orig_text)
        new_text += ' ' + orig_text
    # Recreate the request post object to get a mutable copy
    request.POST = request.POST.copy()

    request.POST['text'] =  new_text
    return get_mattermost_chart(request)

def update_mattermost_chart(request):
    request_body = json.loads(request.body)
    context = request_body['context']

    params = context['params']
    identifiers = params['identifiers']
    span = params['span']

    chart_response = mattermost_chart(request, identifiers, span)

    chart_response = {
        "update": {
            "props": {
                "attachments": chart_response['attachments']
            }
        }
    }
    return HttpResponse(json.dumps(chart_response), content_type="application/json")

def mattermost_chart(request, identifiers, span):
    aggregator = Aggregator()
    indexes = get_indexes(aggregator, identifiers)

    ids = identifiers.upper()
    # Replace slashes with hyphens for safety
    # Slashes could be present in date-formatted string
    ids = ids.replace('/', '-')
    chart_name = ', '.join([p.name for p in indexes])

    # Add a timestamp to the image name to avoid caching future charts
    timestamp = datetime.now().strftime("%H%M%S")
    img_file_name = "{}_{}_{}".format(ids, timestamp, span)

    # Generate the image and cache it in advance
    get_chart_img(request, img_file_name)

    image_path = reverse('quote_img', args=[img_file_name])
    image_url = request.build_absolute_uri(image_path)
    update_url = request.build_absolute_uri(reverse('quote_update'))

    actions = [
        mattermost_action(update_url, 'refresh', identifiers=ids, span=span),
        mattermost_action(update_url, 'day', identifiers=ids, span='day'),
        mattermost_action(update_url, 'week', identifiers=ids, span='week'),
        mattermost_action(update_url, 'month', identifiers=ids, span='month'),
        mattermost_action(update_url, '3 months', identifiers=ids, span='3month'),
        mattermost_action(update_url, 'year', identifiers=ids, span='year'),
        mattermost_action(update_url, '5 years', identifiers=ids, span='5year'),
    ]

    response = {
        "response_type": "in_channel",
        "attachments": [
            {
                "fallback": "{} Chart".format(chart_name),
                "text": chart_name,
                "image_url": image_url,
                "actions": actions
            }
        ]
    }
    return response

def get_indexes(aggregator, identifiers):
    # Remove duplicates by converting to set (and back)
    identifiers = set(identifiers.upper().split(','))
    if len(identifiers) > 10:
        raise BadRequestException("Sorry, you can only quote up to ten stocks/indexes at a time.")

    indexes = []

    if DATABASE_PRESENT:
        # Determine which identifiers, if any, are indexes
        if 'EVERYONE' in identifiers:
            for index in Index.objects.all():
                indexes.append(index)
                identifiers.discard(index.name)
            indexes.append(find_index('VOO'))
            identifiers.discard('EVERYONE')
        else:
            for identifier in list(identifiers):
                index = find_index(identifier)
                if index:
                    indexes.append(index)
                    identifiers.discard(identifier)

    # Load instruments for all index assets and identifiers
    aggregator.load_instruments(*indexes, *identifiers)

    is_single_instrument = (len(identifiers) == 1 and not indexes)

    # Wrap each of the remaining non-index instruments in its own index
    for identifier in identifiers:
        instrument = aggregator.get_instrument(identifier)
        # Use the full name if this instrument is the only thing being quoted
        # Otherwise use its identifier name
        if is_single_instrument:
            index_name = instrument.full_name()
        else:
            index_name = instrument.identifier()
        index = Index(name=index_name)
        asset = Asset(index=index, instrument=instrument, count=1)
        index.add_asset(asset)
        indexes.append(index)

    return indexes

def find_index(name):
    if not re.match('^[A-Z]{1,14}$', name):
        return None

    try:
        return Index.objects.get(name=name)
    except Index.DoesNotExist:
        return None

def stock_info(request):
    symbol = request.POST.get('text', None)

    if not symbol:
        raise BadRequestException("No stock was specified")

    fundamentals = Stock.Fundamentals.get(symbol)
    response = fundamentals.description if fundamentals else 'Stock was not found'
    return mattermost_text(response)

def mattermost_action(url, name, **params):
    return {
        "name": name.capitalize(),
        "integration": {
            "url": url,
            "context": {
                "action": name.lower(),
                "params": params
            }
        }
    }

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
