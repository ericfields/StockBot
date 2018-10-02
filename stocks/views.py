from .utilities import *
from django.views.decorators.cache import cache_page
from django.urls import reverse
from .models import Portfolio
from datetime import datetime
import json
import re

def get_chart(request, identifiers, span = 'day'):
    span = str_to_duration(span)

    # Remove duplicates by converting to set (and back)
    identifiers = list(set(identifiers.split(',')))

    portfolio = None
    hide_value = False
    initial_value = 0

    if len(identifiers) == 1:
        portfolio = find_portfolio(identifiers[0])


    if portfolio:
        instruments = {}
        for asset in portfolio.asset_set.all():
            instruments[asset.instrument()] = asset.count
        # Use portfolio name as title
        chart_name = portfolio.name
        initial_value = portfolio.cash
        hide_value = True
    else:
        instruments = [find_instrument(i) for i in identifiers]
        if len(instruments) == 1:
            chart_name = instruments[0].full_name()
        else:
            chart_name = ', '.join([i.short_name() for i in instruments])

    return chart_img(chart_name, span, instruments, hide_value, initial_value)

def get_mattermost_chart(request):
    body = request.POST.get('text', None)
    if not body:
        raise BadRequestException("No stocks/options specified")
    parts = body.split()
    identifiers = parts[0].upper().split(',')
    if len(parts) > 1:
        span = parts[1]
    else:
        span = 'day'

    chart_response = mattermost_chart(request, identifiers, span)
    return HttpResponse(json.dumps(chart_response), content_type="application/json")

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
    # Raise error if span is invalid
    str_to_duration(span)

    # Remove duplicates by converting to set (and back)
    identifiers = list(set(identifiers))

    portfolio = None

    # Check if this is a request for a portfolio
    if len(identifiers) == 1:
        portfolio = find_portfolio(identifiers[0])
        if portfolio:
            if len(portfolio.asset_set.all()) > 0:
                # Provide the portfolio name as the identifier
                ids = identifiers
                chart_name = identifiers[0]
            else:
                # Empty portfolio, do not chart
                raise BadRequestException("This portfolio is empty")

    if not portfolio:
        instruments = [find_instrument(i) for i in identifiers]
        if len(instruments) == 1:
            chart_name = instruments[0].full_name()
        else:
            chart_name = ', '.join([i.short_name() for i in instruments])

        ids = [i.id for i in instruments]

    # Add a timestamp to the image name to avoid caching future charts
    timestamp = datetime.now().strftime("%H%M%S")
    img_file_name = "{}_{}_{}".format(','.join(ids), timestamp, span)

    image_url = request.build_absolute_uri(reverse('quote_img', args=[img_file_name]))
    update_url = request.build_absolute_uri(reverse('quote_update'))

    actions = [
        mattermost_action(update_url, 'refresh', identifiers=ids, span=span),
        mattermost_action(update_url, 'day', identifiers=ids, span='day'),
        mattermost_action(update_url, 'week', identifiers=ids, span='week'),
        mattermost_action(update_url, 'month', identifiers=ids, span='month'),
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

@cache_page(60 * 15)
def get_chart_img(request, img_name):
    parts = img_name.split("_")
    if len(parts) < 3:
        raise BadRequestException("Invalid image: '{}'".format(img_name))

    identifiers = parts[0].split(',')
    span = str_to_duration(parts[-1])

    portfolio = None
    hide_value = False
    initial_value = 0

    if len(identifiers) == 1:
        portfolio = find_portfolio(identifiers[0])

    if portfolio:
        instruments = {}
        for asset in portfolio.asset_set.all():
            instruments[asset.instrument()] = asset.count
        # Use portfolio name as title
        chart_name = portfolio.name
        initial_value = portfolio.cash
        hide_value = True
    else:
        instruments = [find_instrument(i) for i in identifiers]
        if len(instruments) == 1:
            chart_name = instruments[0].full_name()
        else:
            chart_name = ', '.join([i.short_name() for i in instruments])

    return chart_img(chart_name, span, instruments, hide_value, initial_value)

def chart_img(name, span, instruments, hide_value = False, initial_value = 0):
    chart_data = RobinhoodChartData(name, span, instruments, initial_value)
    chart = Chart(chart_data, hide_value)
    chart_img_data = chart.get_img_data()
    return HttpResponse(chart_img_data, content_type="image/png")


def find_portfolio(name):
    if not re.match('^[A-Z]{1,14}$', name):
        return None

    try:
        return Portfolio.objects.get(name=name)
    except Portfolio.DoesNotExist:
        return None

def valid_format_example_str():
    return "\n\t".join(["{}: {}".format(h.TYPE, h.EXAMPLE) for h in QUOTE_HANDLERS])

def stock_info(request):
    symbol = request.POST.get('text', None)

    if not symbol:
        raise BadRequestException("No stock was specified")

    fundamentals = Fundamentals.get(symbol)
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
