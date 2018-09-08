import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from pytz import timezone
from io import BytesIO

# Define latest time to show on chart
BEFORE_HOURS = '9:00AM'
MARKET_OPEN = '9:30AM'
MARKET_CLOSE = '4:00PM'
AFTER_HOURS = '6:00PM'

MARKET_TIMEZONE = timezone('US/Eastern')

# Set default timezone for plotting all graphs
matplotlib.rcParams['timezone'] = MARKET_TIMEZONE

BEFORE_HOURS_TIME = dateparser.parse(BEFORE_HOURS).time()
MARKET_OPEN_TIME = dateparser.parse(MARKET_OPEN).time()
AFTER_HOURS_TIME = dateparser.parse(AFTER_HOURS).time()
MARKET_CLOSE_TIME = dateparser.parse(MARKET_CLOSE).time()

def time_for_today(selected_time):
    now = datetime.now(MARKET_TIMEZONE)
    if now.time() < BEFORE_HOURS_TIME:
        now = now - timedelta(days=1)
    return now.replace(
        hour=selected_time.hour,
        minute=selected_time.minute,
        second=selected_time.second,
        microsecond=0
    )

# Return market color as RGBA value
def get_market_color(is_positive):
    if is_positive:
        return [0, 0.5, 0, 1] # green
    else:
        return [1, 0, 0, 1] # red

def generate_chart(chart_data):
    series = chart_data.series
    last_closing_price = chart_data.last_closing_price
    current_price = chart_data.current_price
    symbol = chart_data.symbol
    company_name = chart_data.company_name
    span = chart_data.span

    figure, axis = plt.subplots(1, figsize=(7, 3))

    # Week charts are ugly due to gaps in after-hours/weekend trading activity.
    # Re-index these graphs in a way that hides the gaps (at the cost of time accuracy)
    if span == 'week':
        new_index = []
        new_date = series.index[0]
        time_diff = (series.index[-1] - series.index[0]).total_seconds()
        spread_factor = time_diff / len(series.index)
        for n in range(0, len(series.index)):
            new_date += timedelta(seconds=spread_factor)
            new_index.append(new_date)
        series = pd.Series(series.values, index=new_index)

    if company_name:
        if len(company_name) > 64:
            company_name = company_name[0:32] + '...'
        title = ("{} ({})".format(company_name, symbol))
    else:
        title = symbol

    axis.set_title(title, horizontalalignment='left', x=0.0, y=1.15)

    # Format day chart for hourly display and show after-market time
    if span == 'day':
        now = datetime.now(MARKET_TIMEZONE)
        last_time_to_display = time_for_today(AFTER_HOURS_TIME)

        # Indicate times outside trading hours
        market_open_time = time_for_today(MARKET_OPEN_TIME)
        axis.axvspan(series.index[0], market_open_time,
            facecolor='grey', alpha=0.1)

        market_close_time = time_for_today(MARKET_CLOSE_TIME)
        axis.axvspan(market_close_time, last_time_to_display,
            facecolor='grey', alpha=0.1)
        time_format = mdates.DateFormatter("%-I %p")
    else:
        time_diff = series.index[-1] - series.index[0]
        if time_diff < timedelta(weeks=4):
            time_format = mdates.DateFormatter("%-m/%-d")
        else:
            time_format = mdates.DateFormatter("%-m/%y")
        last_time_to_display = series.index[-1]

    axis.xaxis.set_major_formatter(time_format)
    axis.set_xlim(series.index[0], last_time_to_display)

    axis.margins(0.1)
    axis.grid(True, linewidth=0.2)

    # Show the graph as green if the stock's up, or red if it's down
    market_color = get_market_color(current_price >= last_closing_price)

    axis.plot(series, color=market_color)

    if current_price < 0.1:
        current_price_str = '${:,.4f}'.format(current_price)
    else:
        current_price_str = '${:,.2f}'.format(current_price)
    axis.text(0.2, 0.82, current_price_str,
        transform=plt.gcf().transFigure,
        fontsize=15)

    # Show the latest price/change on the graph
    price_change = current_price - last_closing_price
    if price_change >= 0:
        change_sign = '+'
    else:
        change_sign = '-'
    percentage_change = round(price_change / last_closing_price * 100, 2)

    if current_price < 0.1:
        point_change = round(abs(price_change), 4)
    else:
        point_change = round(abs(price_change), 2)
    price_change_str = "{}{} ({}%)".format(change_sign, point_change, percentage_change)
    axis.text(0.4, 0.82, price_change_str,
        transform=plt.gcf().transFigure,
        color = market_color,
        fontsize=12)

    # Show the date/time info
    date_str = datetime.now(MARKET_TIMEZONE).strftime(
        "%-m/%-d/%y %-I:%M %p")
    axis.text(0.73, 0.82, date_str,
        transform=plt.gcf().transFigure,
        color = 'grey',
        fontsize=10)

    figure.subplots_adjust(top=0.8)

    figure_img_data = BytesIO()
    figure.savefig(figure_img_data, format='png', dpi=(100))

    plt.close(figure)

    return figure_img_data.getvalue()
