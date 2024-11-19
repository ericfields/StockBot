from django.core.cache import cache
from django.urls import reverse
from django.http import HttpRequest, HttpResponse
from django.conf import settings

from robinhood.models import Stock
from helpers.utilities import str_to_duration, mattermost_text
from chart import chart_builder

from datetime import datetime
import json

from django.db import connection

from exceptions import BadRequestException

MARKET = 'XNYS'

DATABASE_PRESENT = bool(connection.settings_dict['NAME'])

def get_chart(request, identifiers: list, span = 'day'):
    chart = chart_builder.build_chart(identifiers, span)
    return HttpResponse(chart.get_img_data(), content_type="image/png")

def get_chart_img(request: HttpRequest, img_name: str):
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


def get_mattermost_chart(request: HttpRequest):
    body = request.POST.get('text', '')
    if request.path.endswith('/all'):
        body = 'EVERYONE ' + body

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

def update_mattermost_chart(request: HttpRequest):
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

def build_stockbot_url(request: HttpRequest, uri: str):
    url = request.build_absolute_uri(uri)
    if settings.USE_HTTPS_FOR_URLS:
        url = url.replace('http://', 'https://')
    return url

def mattermost_chart(request: HttpRequest, identifiers: list, span: str):
    ids = identifiers.upper()
    # Replace slashes with hyphens for safety
    # Slashes could be present in date-formatted string
    ids = ids.replace('/', '-')
    chart_name = ', '.join([identifiers])

    # Add a timestamp to the image name to avoid caching future charts
    timestamp = datetime.now().strftime("%H%M%S")
    img_file_name = "{}_{}_{}".format(ids, timestamp, span)

    # Generate the image and cache it in advance
    get_chart_img(request, img_file_name)

    image_path = reverse('quote_img', args=[img_file_name])
    image_url = build_stockbot_url(request, image_path)
    update_url = build_stockbot_url(request, reverse('quote_update'))

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
                "fallback": f"{chart_name} Chart",
                "text": chart_name,
                "image_url": image_url,
                "actions": actions
            }
        ]
    }
    return response

def stock_info(request: HttpRequest):
    symbol = request.POST.get('text', None)

    if not symbol:
        raise BadRequestException("No stock was specified")

    fundamentals = Stock.Fundamentals.get(symbol)
    response = fundamentals.description if fundamentals else 'Stock was not found'
    return mattermost_text(response)

def mattermost_action(url: str, name: str, **params):
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
