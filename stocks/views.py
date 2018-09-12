from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from robinhood import Instrument, Fundamentals
from chart import Chart
from chart_data import ChartData
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from datetime import datetime, timedelta
import json
import re

# Create your views here.
def index(request):
    return HttpResponse("Get outta here.")

@csrf_exempt
def info_GET(request, symbol):
    fundamentals = Fundamentals.get(symbol)
    response = (fundamentals.description if fundamentals else "Stock was not found")
    return HttpResponse(response)

@csrf_exempt
def info_POST(request):
    symbol = request.POST.get('text', None)

    if not symbol:
        return HttpResponse("No stock was specified")

    fundamentals = Fundamentals.get(symbol)
    response = fundamentals.description if fundamentals else 'Stock was not found'
    return HttpResponse(json.dumps({"text": response}), content_type="application/json")

@csrf_exempt
def graph_GET(request, symbol = None, span = 'day'):
    if not symbol:
        if 'symbol' in params:
            symbol = request.GET.get('symbol') or request.GET['text']
        else:
            symbol = request.GET.get('text')

        if not symbol:
            return HttpResponse("No stock was specified")

    instrument = get_instrument(symbol)
    if not instrument:
        return HttpResponse("Stock not found")

    actual_span = __str_to_duration(span)
    if not actual_span:
        return HttpResponseBadRequest("Invalid span '{}'. Must be time unit and/or number, e.g. '3month'".format(span))

    return chart_img(instrument, actual_span)

@csrf_exempt
def graph_POST(request):
    body = request.POST.get('text', None)
    parts = body.split()
    if len(parts) == 0:
        return HttpResponse("No stock was specified")

    symbol = parts[0].upper()
    if len(parts) > 1:
        span = parts[1]
        if not __str_to_duration(span):
            return json_error_response("Invalid span '{}'. Must be time unit and/or number, e.g. '3month'".format(span))
    else:
        span = 'day'

    instrument = get_instrument(symbol)
    if not instrument:
        return json_error_response("Stock '{}' not found".format(symbol))

    img_file_name = "{}_{}_{}.png".format(symbol, datetime.now().strftime("%H%M"), span)

    image_url = request.build_absolute_uri(
        request.get_full_path() + "/image/" + img_file_name)

    response = {
        "response_type": "in_channel",
        "attachments": [
            {
                "fallback": "{} Stock Graph".format(symbol),
                "text": symbol,
                "image_url": image_url
            }
        ]
    }

    return HttpResponse(json.dumps(response), content_type="application/json")

@csrf_exempt
@cache_page(60)
def graph_img(request, img_name):
    parts = img_name.split("_")
    symbol = parts[0]
    if len(parts) > 2:
        span = parts[2]
        actual_span = __str_to_duration(span)
        if not actual_span:
            return HttpResponse("Invalid span '{}'. Must be time unit and/or number, e.g. '3month'".format(span))
    else:
        actual_span = timedelta(days=1)

    instrument = get_instrument(symbol)
    if not instrument:
        return HttpResponse("Stock not found")

    return chart_img(instrument, actual_span)

def chart_img(instrument, span=timedelta(days=1)):
    chart_data = ChartData(instrument, span)
    chart = Chart(chart_data)
    chart_img_data = chart.get_img_data()

    return HttpResponse(chart_img_data, content_type="image/png")

def get_instrument(symbol):
    symbol = symbol.upper()

    instruments = Instrument.search(symbol=symbol)
    if len(instruments) > 0:
        return instruments[0]
    else:
        return None

def json_error_response(text):
    return HttpResponse(json.dumps({"text": text}), content_type="application/json")

def __str_to_duration(duration_str):
    duration_str = duration_str.strip().lower()
    match = re.match('^([0-9]+)?\s*(day|week|month|year|all|d|w|m|y|a)s?$', duration_str)
    if not match:
        return None

    unit = match.groups()[1][0]
    if unit == 'd':
        duration = timedelta(days=1)
    elif unit == 'w':
        duration = timedelta(days=7)
    elif unit == 'm':
        duration = timedelta(days=31)
    elif unit == 'y':
        duration = timedelta(days=365)
    elif unit == 'a':
        # Max duration available is 5 years
        return timedelta(days=365*5)

    if match.groups()[0]:
        # Multiply by provided duration
        duration *= int(match.groups()[0])

    return duration
