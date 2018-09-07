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

# Define latest time to show on chart
MARKET_OPEN = '9:00AM'
AFTER_HOURS = '6:00PM'

MARKET_TIMEZONE = timezone('US/Eastern')

# Set default timezone for plotting all graphs
matplotlib.rcParams['timezone'] = MARKET_TIMEZONE

AFTER_HOURS_TIME = dateparser.parse(AFTER_HOURS).time()
MARKET_OPEN_TIME = dateparser.parse(MARKET_OPEN).time()

def time_for_today(selected_time):
    now = datetime.now(MARKET_TIMEZONE)
    return now.replace(
        hour=selected_time.hour,
        minute=selected_time.minute,
        second=selected_time.second,
        microsecond=0
    )

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

# Return market color as RGBA value
def get_market_color(is_positive):
    if is_positive:
        return [0, 0.5, 0, 1] # green
    else:
        return [1, 0, 0, 1] # red

def generate_chart(symbol, company_name = None):
    series, last_closing_price, current_price = get_robinhood_chart_data(symbol)

    figure, axis = plt.subplots(1, figsize=(7, 3))

    time_format = mdates.DateFormatter("%-I %p")
    axis.xaxis.set_major_formatter(time_format)

    # Show the graph as green if the stock's up, or red if it's down
    market_color = get_market_color(current_price >= last_closing_price)

    axis.text(0.6, 0.9, round(current_price, 2),
        transform=plt.gcf().transFigure,
        fontsize=14)

    if company_name:
        if len(company_name) > 32:
            company_name = company_name[0:32] + '...'
        title = ("{} ({})".format(company_name, symbol))
    else:
        title = symbol

    axis.set_title(title, x=0.2)

    # Fix graph x-axis to market hours
    now = datetime.now(MARKET_TIMEZONE)
    last_time_to_display = time_for_today(AFTER_HOURS_TIME)
    if now < time_for_today(MARKET_OPEN_TIME):
        last_time_to_display -= timedelta(days=1)

    axis.set_xlim(series.index[0], last_time_to_display)

    axis.margins(0.1)
    axis.grid(True, linewidth=0.2)

    axis.plot(series, color=market_color)

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
        color = market_color,
        fontsize=12)

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
