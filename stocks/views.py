from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from robinhood import Instrument, Fundamentals, chart_data
from chart import generate_chart
from chart_data import ChartData
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json

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

    if not valid_span(span):
        return HttpResponse("Invalid span '{}'. Must be one of: day, week, year, 5year, all".format(span))

    return chart_img(instrument, span)

@csrf_exempt
def graph_POST(request):
    body = request.POST.get('text', None)
    parts = body.split()
    if len(parts) == 0:
        return HttpResponse("No stock was specified")

    symbol = parts[0].upper()
    if len(parts) > 1:
        span = valid_span(parts[1])
        if not span:
            return json_error_response("Invalid span '{}'. Must be one of: day, week, year, 5year, all".format(span))
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
def graph_img(request, img_name):
    parts = img_name.split("_")
    symbol = parts[0]
    if len(parts) > 2:
        span = valid_span(parts[2])
        if not span:
            return HttpResponse("Invalid span '{}'. Must be one of: day, week, year, 5year, all".format(span))
    else:
        span = 'day'

    instrument = get_instrument(symbol)
    if not instrument:
        return HttpResponse("Stock not found")

    return chart_img(instrument, span)

def chart_img(instrument, span='day'):
    chart_data = ChartData(instrument, span)
    chart_img_data = generate_chart(chart_data)

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

def valid_span(span):
    span = span.lower()
    valid_spans = {
        'd': 'day',
        'w': 'week',
        'y': 'year',
        '5': '5year',
        'a': 'all'
    }
    if span[0] not in valid_spans:
        return None

    return valid_spans[span[0]]
