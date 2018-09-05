from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from openfigi import get_stock_company
from chart import generate_chart
from io import BytesIO
from .models import Stock
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json

# Create your views here.
def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")

@csrf_exempt
def graph_GET(request, symbol = None):
    if not symbol:
        if 'symbol' in params:
            symbol = request.GET.get('symbol') or request.GET['text']
        else:
            symbol = request.GET.get('text')

        if not symbol:
            return HttpResponse("No stock was specified")

    stock = get_stock(symbol)
    if not stock:
        return HttpResponse("Stock not found")

    return chart_img(stock)

@csrf_exempt

def graph_POST(request):
    symbol = request.POST.get('text', None)

    if not symbol:
        return HttpResponse("No stock was specified")

    symbol = symbol.upper()
    img_file_name = "{}_{}.png".format(symbol, datetime.now().strftime("%H%M"))

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

def graph_img(request, img_name):
    symbol = img_name.split("_")[0]
    stock = get_stock(symbol)
    if not stock:
        return HttpResponse("Stock not found")

    return chart_img(stock)

def chart_img(stock):
    chart = get_chart(stock)

    img_data = BytesIO()
    chart.savefig(img_data, format='png', dpi=(100))

    return HttpResponse(img_data.getvalue(), content_type="image/png")

def get_stock(symbol):
    symbol = symbol.upper()

    stock = None
    try:
        stock = Stock.objects.get(symbol=symbol)
    except ObjectDoesNotExist:
        company_name = get_stock_company(symbol)
        if company_name:
            stock = Stock(symbol=symbol, company_name=company_name)
            stock.save()

    return stock

def get_chart(stock):
    return generate_chart(stock.symbol, stock.company_name)
