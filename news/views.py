from django.shortcuts import render
from django.http import HttpResponse
from robinhood.models import News
from helpers.utilities import html_tag, mattermost_text
from exceptions import BadRequestException

# Sources which tend to write speculation rather than actual news
SPECULATIVE_SOURCES = [
    'seeking_alpha',
    'investorplace',
    'Investopedia',
    'The Motley Fool'
]

def get_news(request, identifier):
    news_items = top_news_items(identifier, 3)
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

    news_items = top_news_items(identifier, max_news_items)
    return mattermost_text(news_items_as_markdown(news_items), in_channel=True)

def top_news_items(identifier, max_news_items):
    news = News.get(identifier)
    if not news.items:
        raise BadRequestException("No news found for stock ticker '{}'.".format(identifier))

    items = filter_sources(SPECULATIVE_SOURCES, news.items)
    if not items:
        raise BadRequestException("No real news available for {} (all speculative).".format(identifier))

    items.sort(key=lambda i: i.num_clicks, reverse=True)
    top_items = items[:max_news_items]
    return top_items

def filter_sources(sources, news_items, whitelist=False):
    filter_lambda = lambda i: (i.api_source in sources or i.source in sources) == whitelist
    return list(filter(filter_lambda, news_items))

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
