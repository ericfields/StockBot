from django.shortcuts import render
from django.http import HttpResponse
from robinhood.models import Stock, News
from helpers.utilities import html_tag, mattermost_text
from exceptions import BadRequestException
import re

# Some sources tend to provide more relevant results than others
PREFERRED_SOURCES = {
    'bloomberg',
    'reuters',
    'fortune'
}

# Sources which tend to write speculation rather than actual news
SPECULATIVE_SOURCES = {
    'seeking_alpha',
    'investorplace',
    'investopedia',
    'the motley fool',
    'benzinga',
    'simply wall st'
}

def get_news(request, identifier):
    news_items = top_news_items(identifier)[:3]
    return HttpResponse(news_items_as_html(news_items))

def get_mattermost_news(request):
    body = request.POST.get('text', None)
    if not body:
        raise BadRequestException("No stocks specified")
    parts = body.split()
    identifier = parts[0].upper()
    if len(parts) > 1:
        try:
            max_news_items = int(parts[-1])
        except ValueError:
            raise BadRequestException("You can only request news for one stock at a time. " +
                "You can optionally specify the number of news items to view as well, e.g. /news FB 3")
        if max_news_items > 10:
            raise BadRequestException("You can only request up to 10 news items.")
        elif max_news_items < 1:
            raise BadRequestException("You must request at least 1 news item.")
    else:
        max_news_items = 1

    news_items = top_news_items(identifier)[:max_news_items]
    return mattermost_text(news_items_as_markdown(news_items), in_channel=True)

def top_news_items(identifier):
    stocks = Stock.search(symbol=identifier)
    if not stocks:
        raise BadRequestException("Stock not found: '{}'".format(identifier))
    stock = stocks[0]
    news = News.get(stock.symbol)

    items = news.items
    if not items:
        raise BadRequestException("No news found for stock ticker '{}'.".format(identifier))

    # Sort initially by popularity, i.e. number of clicks
    items.sort(key=lambda i: i.num_clicks, reverse=True)

    # Filters are defined here for attempting to sort news items by relevance.
    # The priority of the filters mirrors the order they are defined in here.
    filters = []

    # First priority: news items which mention the stock in the title
    filters.append(lambda i: stock.symbol in i.title
        or stock.simple_name.lower() in i.title.lower())
    # Next, news items which mention the stock in the summary
    filters.append(lambda i: stock.symbol in i.summary
        or stock.simple_name.lower() in i.summary.lower())

    # Deprioritize listicles, e.g. "3 reasons why...", "Top 10...", etc.
    number_regex = r"^(Top )?([0-9]+|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
    filters.append(lambda i: not re.match(number_regex, i.title, re.IGNORECASE))

    # Prioritize articles related to only one or two stocks,
    # as these tend to be more relevant to the requested stock.
    filters.append(lambda i: len(i.related_instruments) == 1)
    filters.append(lambda i: len(i.related_instruments) == 2)

    # Prioritize preferred news sources, and deprioritize "speculative" sources
    filters.append(lambda i: source_matches(PREFERRED_SOURCES, i))
    filters.append(lambda i: not source_matches(SPECULATIVE_SOURCES, i))

    # Reorder list using priority filters
    items = prioritize_items(items, *filters)

    return items

def source_matches(sources, news_item):
    sources = set(map(lambda s: s.lower(), sources))

    fields = [news_item.api_source, news_item.source, news_item.title]
    fields = list(map(lambda s: s.lower(), fields))

    matching = any([s for s in sources if any([f for f in fields if s in f])])
    return matching

# Move filtered items to the end of the list
# Priority of each filter is based on the order it is provided in,
# i.e. filters are processed in reverse order
def prioritize_items(items, *filters):
    sorted_items = []
    for f in reversed(filters):
        sorted_items = list(filter(f, items))
        for i in items:
            if i not in sorted_items:
                sorted_items.append(i)
        items = sorted_items

    return sorted_items

def news_items_as_html(news_items):
    html_items = []
    for item in news_items:
        html_items.append(html_tag('h3', item.title))
        html_items.append(html_tag('img', None, src=item.preview_image_url, width=200))
        #html_str += "<img src=\"{}\" width=\"200\"/><br/>".format(item.preview_image_url)
        html_items.append(html_tag('a', item.source, href=item.url))
        html_items.append(html_tag('p', item.summary))
    return '<br/>'.join(html_items)

def news_items_as_markdown(news_items):
    markdown_lines = []
    for item in news_items:
        markdown_lines.append("##### [{}]({})".format(item.title, item.url))
        if len(news_items) == 1:
            markdown_lines.append("![{}]({} =250)".format(item.title, item.preview_image_url))
        markdown_lines.append("[{}]({})".format(item.source, item.url))
        markdown_lines.append("{}".format(item.summary))
    return "\n".join(markdown_lines)
