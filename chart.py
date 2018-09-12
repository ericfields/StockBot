import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from pytz import timezone
from io import BytesIO

from robinhood import Market

# Define latest time to show on chart

MARKET = 'XNYS'

class Chart():
    # Size of the overall chart
    size = (7, 3)

    # Colored areas indicating non-trading hours for day chart
    after_hours_tint = {'facecolor': 'grey', 'alpha': 0.1}

    title_layout = {'horizontalalignment': 'left',
        'x': 0.0, 'y': 1.15}
    max_title_length = 64

    # Style for line indicating the opening price
    initial_price_line_style = {'linestyle': 'dotted', 'color': 'grey'}

    # Color indicating whether security is positive or negative since open
    # Color is defined as an RGBA value (red, green, blue, alpha)
    positive_market_color = [0, 0.5, 0, 1] # green
    negative_market_color = [1, 0, 0, 1] # red

    # Chart margins so that line doesn't touch the Y axis
    margins = 0.1

    # Grid options
    show_grid = True
    grid_style = {'linewidth': 0.1}

    # Time formats
    hourly_format = "%-I %p"
    daily_format = "%-m/%-d"
    monthly_format = "%-m/%y"
    yearly_format = "%Y"

    # Price info display
    price_info_height = 0.82
    current_price_xpos = 0.2
    price_change_xpos = 0.4
    current_price_fontsize = 15
    price_change_fontsize = 12

    # Date position on plot (x,y tuple)
    chart_time_pos = (0.73, 0.82)
    chart_time_str_format = "%-m/%-d/%y %-I:%M %p"

    # Additional spacing at top to accommodate title, price, etc.
    top_spacing = 0.8

    def __init__(self, chart_data):
        self.market_timezone = timezone(Market.get(MARKET).timezone)
        self.market_hours = self.get_market_hours()

        self.series = chart_data.series
        self.initial_price = chart_data.initial_price
        self.current_price = chart_data.current_price
        self.symbol = chart_data.symbol
        self.security_name = chart_data.security_name
        self.span = chart_data.span

        self.figure, self.axis = plt.subplots(1, figsize=self.size)

        timespan = self.series.index[-1] - self.series.index[0]

        # Week charts are ugly due to gaps in after-hours/weekend trading activity.
        # Re-index these graphs in a way that hides the gaps (at the cost of time accuracy)
        if timespan < timedelta(weeks=2):
            self.__normalize_indices()

        self.__show_title()

        self.axis.xaxis_date(self.market_timezone)

        self.axis.set_xlim(left=self.series.index[0])

        # Format chart depending on data time span
        if timespan <= timedelta(days=1):
            time_format = self.hourly_format
            self.__show_day_chart_options()
        elif timespan < timedelta(weeks=4):
            time_format = self.daily_format
        elif timespan < timedelta(weeks=208):
            time_format = self.monthly_format
        else:
            time_format = self.yearly_format
        self.axis.xaxis.set_major_formatter(
            mdates.DateFormatter(time_format, self.market_timezone)
        )

        # Add current price to long-term graph if it has changed after hours
        if timespan > timedelta(days=1):
            last_time = self.series.index[-1]
            if self.series[last_time] != self.current_price:
                time_delta = last_time - self.series.index[-2]
                self.series.at[last_time + time_delta] = self.current_price

            self.axis.set_xlim(right=self.series.index[-1])


        self.axis.margins(self.margins)
        self.axis.grid(self.show_grid, **self.grid_style)

        self.__show_price_info()

        self.__show_chart_date()

        self.figure.subplots_adjust(top=self.top_spacing)

    def get_market_hours(self):
        market_hours = Market.hours(MARKET, datetime.now())
        if not market_hours.is_open or datetime.now() < market_hours.extended_opens_at:
            # Get market hours for the previous open day
            date = market_hours.previous_open_hours.split('/')[-2]
            market_hours = Market.hours(MARKET, date)
        return market_hours

    def get_img_data(self):
        self.axis.plot(self.series, color=self.__get_market_color())

        figure_img_data = BytesIO()
        self.figure.savefig(figure_img_data, format='png', dpi=(100))
        plt.close(self.figure)

        return figure_img_data.getvalue()

    def __normalize_indices(self):
        new_index = []
        new_date = self.series.index[0]
        time_diff = (self.series.index[-1] - self.series.index[0]).total_seconds()
        spread_factor = time_diff / len(self.series.index)
        for n in range(0, len(self.series.index)):
            new_date += timedelta(seconds=spread_factor)
            new_index.append(new_date)
        self.series = pd.Series(self.series.values, index=new_index)

    def __show_title(self):
        if self.security_name:
            if len(self.security_name) > self.max_title_length:
                self.security_name = self.security_name[0:max_title_length] + '...'
            title = ("{} ({})".format(self.security_name, self.symbol))
        else:
            title = self.symbol

        self.axis.set_title(title, **self.title_layout)

    def __show_price_info(self):
        # Show the graph as green if the stock's up, or red if it's down
        market_color = self.__get_market_color()

        if self.current_price < 0.1:
            self.current_price_str = '${:,.4f}'.format(self.current_price)
        else:
            self.current_price_str = '${:,.2f}'.format(self.current_price)
        self.axis.text(self.current_price_xpos, self.price_info_height, self.current_price_str,
            transform=plt.gcf().transFigure,
            fontsize=self.current_price_fontsize)

        # Show the latest price/change on the graph
        price_change = self.current_price - self.initial_price
        if price_change >= 0:
            change_sign = '+'
        else:
            change_sign = '-'
        percentage_change = round(price_change / self.initial_price * 100, 2)

        if self.current_price < 0.1:
            point_change = round(abs(price_change), 4)
        else:
            point_change = round(abs(price_change), 2)
        price_change_str = "{}{} ({}%)".format(change_sign, point_change, percentage_change)
        self.axis.text(self.price_change_xpos, self.price_info_height, price_change_str,
            transform=plt.gcf().transFigure,
            color = market_color,
            fontsize=self.price_change_fontsize)

    def __show_day_chart_options(self):
        now = datetime.now(self.market_timezone)

        # Indicate times outside trading hours
        market_open_time = self.market_hours.opens_at
        self.axis.axvspan(self.series.index[0], market_open_time,
            **self.after_hours_tint)

        # Add a dashed line indicating the opening price
        self.axis.axhline(self.initial_price,
            **self.initial_price_line_style)

        market_close_time = self.market_hours.closes_at
        self.axis.axvspan(market_close_time, self.market_hours.extended_closes_at,
            **self.after_hours_tint)

        self.axis.set_xlim(right=self.market_hours.extended_closes_at)

    def __show_chart_date(self):
        # Show the date/time info
        date_str = datetime.now(self.market_timezone).strftime(
            self.chart_time_str_format)
        self.axis.text(self.chart_time_pos[0], self.chart_time_pos[1], date_str,
            transform=plt.gcf().transFigure,
            color = 'grey',
            fontsize=10)

    # Return graph color depending on whether price is up or down
    def __get_market_color(self):
        if self.current_price >= self.initial_price:
            return self.positive_market_color
        else:
            return self.negative_market_color
