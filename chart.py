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
    # Re-index these graphs in a way that hides the gaps (at the cost of accuracy)
    if span == 'week':
        new_index = []
        start_date = series.index[0]
        date_diff = series.index[1] - series.index[0]
        for n in range(0, len(series.index)):
            # The ratio of 24 hours in a day to the 6.5 business hours in a trading day
            # is 24 / 6.5, or about 3.692. We use this multiple to determine how to
            # space out these new fake timestamps
            new_date = start_date + timedelta(seconds=date_diff.seconds * 3.692 * n)
            new_index.append(new_date)
        series = pd.Series(series.values, index=new_index)

    if company_name:
        if len(company_name) > 32:
            company_name = company_name[0:32] + '...'
        title = ("{} ({})".format(company_name, symbol))
    else:
        title = symbol

    axis.set_title(title, x=0.2)

    # Format day chart for hourly display and show after-market time
    if span == 'day':
        now = datetime.now(MARKET_TIMEZONE)
        last_time_to_display = time_for_today(AFTER_HOURS_TIME)
        if now < time_for_today(MARKET_OPEN_TIME):
            last_time_to_display -= timedelta(days=1)

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

    axis.text(0.55, 0.9, "${}".format(round(current_price, 2)),
        transform=plt.gcf().transFigure,
        fontsize=14)

    # Show the latest price/change on the graph
    price_change = round(current_price - last_closing_price, 2)
    if price_change > 0:
        change_sign = '+'
    else:
        change_sign = '-'
    percentage_change = round(price_change / last_closing_price * 100, 2)

    price_change_str = "{}{} ({}%)".format(change_sign, abs(price_change), percentage_change)
    axis.text(0.73, 0.9, price_change_str,
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
