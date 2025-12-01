from typing import Any
from django.core.cache import cache
from django.urls import reverse
from django.http import HttpRequest, HttpResponse
from django.conf import settings

from robinhood.models import Stock
from helpers.utilities import mattermost_text
from chart import chart_builder

from datetime import datetime
import json

from django.db import connection

from exceptions import BadRequestException

MARKET = 'XNYS'

DATABASE_PRESENT = bool(connection.settings_dict['NAME'])

def get_chart(request, identifiers: list, span = 'day'):
    chart = chart_builder.build_chart(identifiers, span, split=bool_param(request, 'split'))
    return HttpResponse(chart.get_img_data(), content_type="image/png")

def get_chart_img(request: HttpRequest, img_name: str):
    cache_key = get_cache_key(img_name, request)
    if cache.has_key(cache_key):
        return cache.get(cache_key)

    parts = img_name.split("_")
    if len(parts) < 3:
        raise BadRequestException("Invalid image: '{}'".format(img_name))
    identifiers = parts[0]
    span = parts[-1]

    response = get_chart(request, identifiers, span)
    cache.set(cache_key, response)
    return response

def get_cache_key(img_name: str, request: HttpRequest):
    key = img_name
    if bool_param(request, 'split'):
        key += '_split'
    return key


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

    params: dict[str, Any] = context['params']
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

    url_params = ''
    if bool_param(request, 'split'):
        url_params = '?split=true'

    image_path = reverse('quote_img', args=[img_file_name]) + url_params
    image_url = build_stockbot_url(request, image_path)
    update_url = build_stockbot_url(request, reverse('quote_update') + url_params)

    params = {
        'identifiers': ids
    }

    name_to_span = {
        'refresh': span,
        'day': 'day',
        'week': 'week',
        'month': 'month',
        '3 months': '3month',
        'year': 'year',
        '5 years': '5year'
    }

    actions = create_mattermost_actions(update_url, name_to_span, params)

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

def create_mattermost_actions(update_url: str, name_to_span: dict[str, str], params: dict[str, Any]) -> list[dict[str, str | dict]]: 
    actions = []
    for name in name_to_span:
        span = name_to_span[name]
        action = mattermost_action(update_url, name, span=span, **params)
        actions.append(action)

    return actions

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

def bool_param(request: HttpRequest, param_name: str) -> bool:
    value = request.GET.get(param_name)
    return is_truthy(value)

def is_truthy(value: str):
    if value != None:
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            value = value.lower()
            match value:
                case 'true' | 't' | 'y' | '1':
                    return True
    return False