from alpha_vantage.timeseries import TimeSeries
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import pytz
import config
import pandas as pd
from time import sleep

API_KEY = config.alphavantage_api_key

TS = TimeSeries(key=API_KEY, output_format='pandas')

def get_chart_data(symbol, start_date):
    while True:
        try:
            data, meta_data = TS.get_intraday(symbol=symbol,interval='1min',outputsize='full')
        except ValueError as e:
            if "API call volume" in str(e):
                print("Warning: Requests are now being throttled")
                sleep(30)
                continue
            else:
                raise e
        break


    # Use the closing price at each time as the plotted value
    data = data['4. close']

    time_values = []
    price_values = []

    # iterates through today data and appends date & price lists with data and price data for lookback period
    for date_str in data.keys():
        date = pd.to_datetime(date_str)
        if (date >= start_date):
            time_values.append(date)
            price_values.append(data[date_str])

    df_today = pd.DataFrame(data={'Time': time_values, 'Price': price_values})

    df_today.set_index(['Time'], inplace = True)


    return df_today

def generate_chart(symbol, company_name = None):
    now = datetime.now()
    start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if start_time > now:
        # It's after midnight, use the previous day's results instead
        start_time = start_time - timedelta(days=1)

    end_time = start_time.replace(hour=16, minute=30)

    df = get_chart_data(symbol, start_time)

    figure, axis = plt.subplots(1, figsize=(7, 3))

    time_format = mdates.DateFormatter("%-I %p")
    axis.xaxis.set_major_formatter(time_format)

    open_price = df['Price'][0]
    last_price = df['Price'][-1]

    # Show the graph as green if the stock's up, or red if it's down
    options = {}
    if last_price >= open_price:
        options['color'] = 'green'
    else:
        options['color'] = 'red'

    axis.text(0.6, 0.9, round(last_price, 2),
        transform=plt.gcf().transFigure,
        fontsize=14)

    if company_name:
        title = ("{} ({})".format(company_name, symbol))
    else:
        title = symbol

    axis.set_title(title, x=0.2)
    axis.set_xlim(start_time, end_time)

    axis.grid(True, linewidth=0.2)

    axis.plot(df, **options)

    # Show the latest price/change on the graph
    price_change = round(last_price - open_price, 2)
    if price_change > 0:
        change_sign = '+'
    else:
        change_sign = '-'
    percentage_change = round(price_change / open_price * 100, 2)

    price_change_str = "{}{} ({}%)".format(change_sign, abs(price_change), percentage_change)
    axis.text(0.7, 0.9, price_change_str,
        transform=plt.gcf().transFigure,
        color = options['color'],
        fontsize=10)

    # Show the date/time info
    date_str = now.replace(tzinfo=pytz.timezone('EST')).strftime(
        "%-m/%-d/%y %-I:%M %p")
    axis.text(0.7, 0.8, date_str,
        transform=plt.gcf().transFigure,
        color = 'grey',
        fontsize=10)

    return figure
