from uuid import uuid4
from robinhood.models import *
from robinhood.option_handler import OptionHandler
from datetime import date, datetime, timedelta
from pytz import timezone
import time
import random

option_handler = OptionHandler()

def mock_market():
    now = datetime.now(timezone('US/Eastern'))
    # Rebuild to make it timezone-unaware while still keeping the correct timezone-aware date
    now = datetime(year=now.year, month=now.month, day=now.day)
    market = Market(
        name='New York Stock Exchange',
        acronym='NYSE',
        mic='XNYS',
        timezone='US/Eastern',
    )
    market_hours = Market.Hours(
        opens_at=now.replace(hour=9, minute=30),
        extended_opens_at=now.replace(hour=9, minute=0),
        closes_at=now.replace(hour=16, minute=0),
        extended_closes_at=now.replace(hour=18, minute=0),
        is_open=True
    )
    Market.mock_get(market, 'XNYS')
    Market.Hours.mock_get(market_hours, "https://api.robinhood.com/markets/{}/hours/{}/"
        .format(market.mic, now.date())
    )

def mock_index_workflow(index_name, *stock_symbols):
    # Ensure that the check for a preexisting stock
    # with the same name as the index is mocked
    Stock.mock_search([], symbol=index_name)
    if stock_symbols:
        mock_stock_workflow(*stock_symbols)

def mock_stock_workflow(*symbols):
    stocks = [mock_stock(s) for s in symbols]
    quotes = [mock_stock_quote(s) for s in stocks]
    historicals = [mock_stock_historicals(s) for s in stocks]

    instrument_urls=[s.url for s in stocks]

    Stock.mock_search(stocks, ids=[s.id for s in stocks])
    Stock.Quote.mock_search(quotes, instruments=instrument_urls)
    Stock.Historicals.mock_search(historicals, instruments=instrument_urls,
        span='day', interval='5minute', bounds='trading')
    if len(stocks) == 1:
        return stocks[0]
    else:
        return stocks

def mock_stock(symbol, name=None):
    if Stock.has_mock(symbol=symbol):
        return Stock.search(symbol=symbol)[0]

    if not name:
        name = symbol.capitalize()
    id = str(uuid4())
    stock = Stock(
        id=id,
        symbol=symbol,
        simple_name=name,
        name=name + ", Inc.",
        url='https://api.robinhood.com/instruments/' + id + '/'
    )
    Stock.mock_get(stock, stock.id)
    Stock.mock_search(stock, symbol=stock.symbol)
    return stock

def mock_stock_quote(instrument, price=random.uniform(10,100)):
    quote = Stock.Quote(
        symbol=instrument.symbol,
        last_trade_price=price,
        last_extended_hours_trade_price=price*0.9,
        previous_close=price*0.9,
        updated_at=datetime.now(),
        instrument=instrument.url
    )
    return quote

def mock_stock_historicals(instrument, span='day'):
    span = span.lower()
    now = datetime.now()
    if span == 'day':
        time = now - timedelta(days=1)
        interval_str = '5minute'
        interval = timedelta(minutes=5)
    elif span == 'week':
        time = now - timedelta(days=7)
        interval_str = '10minute'
        interval = timedelta(minutes=10)
    elif span == 'month':
        time = now - timedelta(days=30)
        interval_str = 'hour'
        interval = timedelta(hours=1)
    elif span == 'year':
        time = now - timedelta(days=365)
        interval_str = 'day'
        interval = timedelta(days=1)

    historicals_items= []
    while time <= now:
        historicals_items.append(Stock.Historicals.Item(
            begins_at=time,
            open_price=random.uniform(10, 100),
            close_price=random.uniform(10, 100),
            interpolated=False
        ))
        time += interval
    return Stock.Historicals(
        instrument=instrument.url,
        symbol=instrument.symbol,
        span=span,
        interval=interval_str,
        bounds='trading',
        items=historicals_items
    )

def mock_option_workflow(*identifiers):
    options = [mock_option(*option_handler.parse_option(i)) for i in identifiers]

    stocks = [mock_stock(o.chain_symbol) for o in options]
    Stock.mock_search(stocks, ids=[s.id for s in stocks])

    quotes = [mock_option_quote(o) for o in options]
    historicals = [mock_option_historicals(o) for o in options]

    instrument_urls=[o.url for o in options]

    [Option.mock_search(o, chain_symbol=o.chain_symbol,
        type=o.type,
        strike_price=o.strike_price,
        expiration_date=o.expiration_date,
        state=o.state
    ) for o in options]
    Option.mock_search(options, ids=[o.id for o in options])
    Option.Quote.mock_search(quotes, instruments=instrument_urls)
    Option.Historicals.mock_search(historicals, instruments=instrument_urls,
        span='day', interval='5minute', bounds='trading')
    if len(options) == 1:
        return options[0]
    else:
        return options

def mock_option(chain_symbol, strike_price, type, expiration_date):
    id = str(uuid4())
    chain_id = str(uuid4())
    option_expiration_date = expiration_date or date.today()
    option = Option(
        id=id,
        issue_date=option_expiration_date - timedelta(days=7),
        tradability='tradeable',
        strike_price=strike_price,
        expiration_date=option_expiration_date,
        chain_id=chain_id,
        type=type,
        chain_symbol=chain_symbol,
        tradeable=True,
        state='active',
        url='https://api.robinhood.com/options/instruments/' + id + '/'
    )

    search_params = {
        'chain_symbol': option.chain_symbol,
        'type': option.type,
        'strike_price': option.strike_price
    }

    if expiration_date:
        search_params['expiration_date'] = expiration_date
    else:
        search_params['state'] = 'active'

    Option.mock_search(option, **search_params)
    return option

def mock_option_quote(instrument, price=random.uniform(10,100)):
    return Option.Quote(
        adjusted_mark_price=price,
        previous_close_price=price*0.9,
        instrument=instrument.url
    )

def mock_option_historicals(instrument, span='day'):
    span = span.lower()
    now = datetime.now()
    if span == 'day':
        time = now - timedelta(days=1)
        interval_str = '5minute'
        interval = timedelta(minutes=5)
    elif span == 'week':
        time = now - timedelta(days=7)
        interval_str = '10minute'
        interval = timedelta(minutes=10)
    elif span == 'month':
        time = now - timedelta(days=30)
        interval_str = 'hour'
        interval = timedelta(hours=1)
    elif span == 'year':
        time = now - timedelta(days=365)
        interval_str = 'day'
        interval = timedelta(days=1)

    historicals_items= []
    while time <= now:
        historicals_items.append(Option.Historicals.Item(
            begins_at=time,
            open_price=random.uniform(10, 100),
            close_price=random.uniform(10, 100),
            interpolated=False
        ))
        time += interval
    return Option.Historicals(
        instrument=instrument.url,
        span=span,
        interval=interval_str,
        bounds='trading',
        items=historicals_items
    )

def mock_news(stock):
    symbol = stock.symbol
    news_items = []
    for i in range(0, 10):
        news_items.append(News.Item(
            url=f"https://fakenews.com/{i}",
            api_source='CNBC',
            source='CNBC',
            title=f"{symbol} news {i}",
            author="Newsy news",
            summary=f"News on {symbol} {i}",
            instrument=stock.url,
            num_clicks=0,
            preview_image_url=None,
            published_at=datetime.now(),
            updated_at=datetime.now(),
            related_instruments=[stock.url]
        ))
    news = News(items=news_items)
    News.mock_get(news, 'FB')
    return news
