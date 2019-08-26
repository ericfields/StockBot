import re
from exceptions import BadRequestException
from robinhood.stock_handler import StockHandler
from robinhood.option_handler import OptionHandler
from django.http import HttpResponse
from datetime import timedelta
from uuid import UUID
import json

DURATION_FORMAT = '^([0-9]+)?\s*(day|week|month|year|all|d|w|m|y|a)s?$'

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

def mattermost_text(text, icon_url=None, in_channel=False):
    params = {'text': text}
    if in_channel:
        params['response_type'] = 'in_channel'
    if icon_url:
        params['icon_url'] = icon_url
    return HttpResponse(json.dumps(params), content_type='application/json')

def mattermost_table(rows):
    if not rows:
        raise Exception("At least one row is required to generate a Mattermost table")

    header_row_columns = rows.pop(0)
    table_text = '|' + '|'.join(header_row_columns) + "|\n|" + "|".join(["----"] * len(header_row_columns)) + "|"
    for columns in rows:
        table_text += "\n|" + '|'.join(columns) + '|'
    return table_text


QUOTE_HANDLERS = [StockHandler, OptionHandler]
def valid_format_example_str():
    return "\n\t".join(["{}: {}".format(h.TYPE, h.EXAMPLE) for h in QUOTE_HANDLERS])

def html_tag(type, body, **attrs):
    html_str = "<{}".format(type)
    if attrs:
        attr_str = ""
        for attr in attrs:
            attr_str += "{}=\"{}\" ".format(attr, attrs[attr])
        html_str += " {}".format(attr_str)
    if body:
        html_str += ">{}</{}>".format(body, type)
    else:
        html_str += "/>"
    return html_str
