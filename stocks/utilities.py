import re
from .exceptions import BadRequestException, ForbiddenException
from robinhood.chart_data import RobinhoodChartData
from django.http import HttpResponse
from datetime import datetime, timedelta
from chart import Chart
import json

DURATION_FORMAT = '^([0-9]+)?\s*(day|week|month|year|all|d|w|m|y|a)s?$'

def chart_img(name, span, instruments):
    chart_data = RobinhoodChartData(name, span, instruments)
    chart = Chart(chart_data)
    chart_img_data = chart.get_img_data()
    return HttpResponse(chart_img_data, content_type="image/png")

def str_to_duration(duration_str):
    duration_str = duration_str.strip().lower()
    match = re.match(DURATION_FORMAT, duration_str)
    if not match:
        raise BadRequestException("Invalid span '{}'. Must be time unit and/or number, e.g. '3month'".format(duration_str))

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

def mattermost_text(text):
    return HttpResponse(json.dumps({"text": text}), content_type="application/json")

def mattermost_chart(request, chart_name, span, entities):
    entity_ids = ','.join(entity.id for entity in entities)

    img_file_name = "{}_{}_{}.png".format(entity_ids, datetime.now().strftime("%H%M"), span)

    image_url = request.build_absolute_uri(
        request.get_full_path() + "/image/" + img_file_name)

    response = {
        "response_type": "in_channel",
        "attachments": [
            {
                "fallback": "{} Chart".format(chart_name),
                "text": chart_name,
                "image_url": image_url
            }
        ]
    }

    return HttpResponse(json.dumps(response), content_type="application/json")
