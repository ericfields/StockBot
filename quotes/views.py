from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.urls import reverse
from django.http import HttpResponse

from portfolios.models import Portfolio, Asset
from robinhood.models import Stock, Market
from helpers.utilities import str_to_duration, mattermost_text, find_instrument
from chart.chart import Chart
from chart.chart_data import ChartData
from quotes.aggregator import quote_aggregate, historicals_aggregate

from datetime import datetime, timedelta
import json
import re

MARKET = 'XNYS'

def get_chart(request, identifiers, span = 'day'):
    span = str_to_duration(span)
    portfolios = get_portfolios(span, identifiers)

    # Hide the pricing information for a user portfolio
    hide_value = any([p.pk for p in portfolios])

    title = ', '.join([p.name for p in portfolios])

    chart_data_sets = [ChartData(p) for p in portfolios]
    portfolios = [cd.portfolio for cd in chart_data_sets]
    quotes = quote_aggregate(*portfolios)

    market = Market.get(MARKET)
    market_hours = market.hours()
    if not (market_hours.is_open and datetime.now() >= market_hours.extended_opens_at):
        # Get the most recent open market hours, and change the start/end time accordingly
        market_hours = market_hours.previous_open_hours()

    start_time, end_time = get_start_and_end_time(market_hours, span)
    historicals = historicals_aggregate(start_time, end_time, *portfolios)

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
        raise BadRequestException("No stocks/options/portfolios specified")
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
    portfolios = get_portfolios(str_to_duration(span), identifiers)

    ids = identifiers.upper()
    chart_name = ', '.join([p.name for p in portfolios])

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

def get_portfolios(span, identifiers):
    # Remove duplicates by converting to set (and back)
    identifiers = list(set(identifiers.upper().split(',')))
    if len(identifiers) > 10:
        raise BadRequestException("Sorry, you can only quote up to ten stocks/portfolios at a time.")

    if any([i == 'EVERYONE' for i in identifiers]):
        return Portfolio.objects.all()

    portfolios = []
    instruments = []

    for identifier in identifiers:
        # Check if this is a user portfolio
        portfolio = find_portfolio(identifier)
        if portfolio:
            portfolios.append(portfolio)
        else:
            # No portfolio with this identifier exists; must be an instrument.
            instruments.append(find_instrument(identifier))

    # Create a single portfolio for any remaining instruments
    if instruments:
        # Create a portfolio for the instruments
        portfolio = Portfolio()
        for instrument in instruments:
            asset = Asset(portfolio=portfolio, instrument=instrument, count=1)
            portfolio.add_asset(asset)
        if len(instruments) == 1 and not portfolios:
            portfolio.name = instruments[0].full_name()
        else:
            portfolio.name = ', '.join([i.identifier() for i in instruments])
        portfolios.append(portfolio)

    return portfolios

def find_portfolio(name):
    if not re.match('^[A-Z]{1,14}$', name):
        return None

    try:
        return Portfolio.objects.get(name=name)
    except Portfolio.DoesNotExist:
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
