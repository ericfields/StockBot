import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from pytz import timezone
import pandas as pd
from time import sleep
import robinhood
from multiprocessing.pool import ThreadPool
from io import BytesIO

# Define time range to show on chart
MARKET_OPEN = '9:30AM'
MARKET_CLOSE = '4:00PM'

MARKET_TIMEZONE = timezone('US/Eastern')

# Set default timezone for plotting all graphs
matplotlib.rcParams['timezone'] = MARKET_TIMEZONE

MARKET_OPEN_TIME = dateparser.parse(MARKET_OPEN).time()
MARKET_CLOSE_TIME = dateparser.parse(MARKET_CLOSE).time()

def get_market_times():
    now = datetime.now(MARKET_TIMEZONE)
    market_open = now.replace(
        hour=MARKET_OPEN_TIME.hour,
        minute=MARKET_OPEN_TIME.minute,
        second=MARKET_OPEN_TIME.second,
        microsecond=0
    )
    if market_open > now:
        # It's after midnight, use the previous day's results instead
        market_open = market_open - timedelta(days=1)

    market_close = market_open.replace(
        hour=MARKET_CLOSE_TIME.hour,
        minute=MARKET_CLOSE_TIME.minute,
        second=MARKET_CLOSE_TIME.second,
        microsecond=0
    )
    return market_open, market_close

def get_robinhood_chart_data(symbol):
    pool = ThreadPool(processes=1)
    quote_thread_result = pool.apply_async(robinhood.quote, (symbol,))

    historical_data = robinhood.historicals(symbol)

    time_values = []
    price_values = []
    for historical in historical_data['historicals']:
        time_values.append(dateparser.parse(historical['begins_at']))
        price_values.append(float(historical['close_price']))

    last_closing_price = float(historical_data['previous_close_price'])

    quote_data = quote_thread_result.get()
    current_price = float(quote_data['last_trade_price'])

    return pd.Series(price_values, index=time_values), last_closing_price, current_price

def generate_chart(symbol, company_name = None):
    series, last_closing_price, current_price = get_robinhood_chart_data(symbol)

    figure, axis = plt.subplots(1, figsize=(7, 3))

    time_format = mdates.DateFormatter("%-I %p")
    axis.xaxis.set_major_formatter(time_format)

    # Show the graph as green if the stock's up, or red if it's down
    options = {}
    if current_price >= last_closing_price:
        options['color'] = 'green'
    else:
        options['color'] = 'red'

    axis.text(0.6, 0.9, round(current_price, 2),
        transform=plt.gcf().transFigure,
        fontsize=14)

    if company_name:
        title = ("{} ({})".format(company_name, symbol))
    else:
        title = symbol

    axis.set_title(title, x=0.2)

    # Fix graph x-axis to market hours
    market_open, market_close = get_market_times()
    axis.set_xlim(market_open, market_close)

    # Fix graph y-axis to max/min prices available
    min_price = min(min(series), last_closing_price)
    max_price = max(max(series), last_closing_price)
    axis.set_ylim(min_price - min_price * .01, max_price + max_price * .01)

    axis.grid(True, linewidth=0.2)

    axis.plot(series, **options)

    # Show the latest price/change on the graph
    price_change = round(current_price - last_closing_price, 2)
    if price_change > 0:
        change_sign = '+'
    else:
        change_sign = '-'
    percentage_change = round(price_change / last_closing_price * 100, 2)

    price_change_str = "{}{} ({}%)".format(change_sign, abs(price_change), percentage_change)
    axis.text(0.8, 0.9, price_change_str,
        transform=plt.gcf().transFigure,
        color = options['color'],
        fontsize=10)

    # Show the date/time info
    date_str = datetime.now(MARKET_TIMEZONE).strftime(
        "%-m/%-d/%y %-I:%M %p")
    axis.text(0.7, 0.8, date_str,
        transform=plt.gcf().transFigure,
        color = 'grey',
        fontsize=10)

    figure_img_data = BytesIO()
    figure.savefig(figure_img_data, format='png', dpi=(100))

    plt.close(figure)

    return figure_img_data.getvalue()
