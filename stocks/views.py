from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from robinhood import Instrument, Fundamentals
from chart import generate_chart
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
def graph_GET(request, symbol = None):
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

    return chart_img(instrument)

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
            response = {"text": "Invalid span '{}'. Must be one of: day, week, year, 5year, all".format(span)}
            return HttpResponse(response, content_type="application/json")
    else:
        span = 'day'

    instrument = get_instrument(symbol)
    if not instrument:
        response = {"text": "Stock '{}' not found".format(symbol)}
        return HttpResponse(response, content_type="application/json")

    img_file_name = "{}_{}_{}.png".format(symbol, span, datetime.now().strftime("%H%M"))

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

def valid_span(span):
    valid_spans = {
        'd': 'day',
        'w': 'week',
        'y': 'year',
        '5': '5year',
        'a': 'all'
    }
    if span[0] not in valid_spans:
        return None

    return span[0].lower()

def graph_img(request, img_name):
    symbol = img_name.split("_")[0]
    instrument = get_instrument(symbol)
    if not instrument:
        return HttpResponse("Stock not found")

    return chart_img(instrument)

def chart_img(instrument):
    chart_img_data = get_chart_img_data(instrument)

    return HttpResponse(chart_img_data, content_type="image/png")

def get_instrument(symbol):
    symbol = symbol.upper()

    instruments = Instrument.search(symbol=symbol)
    if len(instruments) > 0:
        return instruments[0]
    else:
        return None

def get_chart_img_data(instrument):
    return generate_chart(instrument.symbol, instrument.simple_name or instrument.name)
