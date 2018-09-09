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
    def __init__(self, chart_data):
        self.market_timezone = timezone(Market.get(MARKET).timezone)
        self.market_hours = self.get_market_hours()

        self.series = chart_data.series
        self.last_closing_price = chart_data.last_closing_price
        self.current_price = chart_data.current_price
        self.symbol = chart_data.symbol
        self.company_name = chart_data.company_name
        self.span = chart_data.span

        self.figure, self.axis = plt.subplots(1, figsize=(7, 3))


        # Week charts are ugly due to gaps in after-hours/weekend trading activity.
        # Re-index these graphs in a way that hides the gaps (at the cost of time accuracy)
        if self.span == 'week':
            self.__normalize_indices()

        if self.company_name:
            if len(self.company_name) > 64:
                self.company_name = self.company_name[0:32] + '...'
            title = ("{} ({})".format(self.company_name, self.symbol))
        else:
            title = self.symbol

        self.axis.set_title(title, horizontalalignment='left', x=0.0, y=1.15)

        self.axis.xaxis_date(self.market_timezone)

        # Format day chart for hourly display and show after-market time
        if self.span == 'day':
            now = datetime.now(self.market_timezone)
            last_time_to_display = self.market_hours.extended_closes_at

            # Indicate times outside trading hours
            market_open_time = self.market_hours.opens_at
            self.axis.axvspan(self.series.index[0], market_open_time,
                facecolor='grey', alpha=0.1)

            # Add a dashed line indicating the opening price
            self.axis.axhline(self.last_closing_price,
                linestyle='dotted', color='grey', linewidth=1.2)

            market_close_time = self.market_hours.closes_at
            self.axis.axvspan(market_close_time, last_time_to_display,
                facecolor='grey', alpha=0.1)
            time_format = mdates.DateFormatter("%-I %p", self.market_timezone)
        else:
            time_diff = self.series.index[-1] - self.series.index[0]
            if time_diff < timedelta(weeks=4):
                time_format = mdates.DateFormatter("%-m/%-d")
            else:
                time_format = mdates.DateFormatter("%-m/%y")
            last_time_to_display = self.series.index[-1]

        self.axis.xaxis.set_major_formatter(time_format)
        self.axis.set_xlim(self.series.index[0], last_time_to_display)

        self.axis.margins(0.1)
        self.axis.grid(True, linewidth=0.2)

        self.current_price = self.current_price
        self.last_closing_price = self.last_closing_price

        # Show the graph as green if the stock's up, or red if it's down
        market_color = self.__get_market_color()

        if self.current_price < 0.1:
            self.current_price_str = '${:,.4f}'.format(self.current_price)
        else:
            self.current_price_str = '${:,.2f}'.format(self.current_price)
        self.axis.text(0.2, 0.82, self.current_price_str,
            transform=plt.gcf().transFigure,
            fontsize=15)

        # Show the latest price/change on the graph
        price_change = self.current_price - self.last_closing_price
        if price_change >= 0:
            change_sign = '+'
        else:
            change_sign = '-'
        percentage_change = round(price_change / self.last_closing_price * 100, 2)

        if self.current_price < 0.1:
            point_change = round(abs(price_change), 4)
        else:
            point_change = round(abs(price_change), 2)
        price_change_str = "{}{} ({}%)".format(change_sign, point_change, percentage_change)
        self.axis.text(0.4, 0.82, price_change_str,
            transform=plt.gcf().transFigure,
            color = self.__get_market_color(),
            fontsize=12)

        # Show the date/time info
        date_str = datetime.now(self.market_timezone).strftime(
            "%-m/%-d/%y %-I:%M %p")
        self.axis.text(0.73, 0.82, date_str,
            transform=plt.gcf().transFigure,
            color = 'grey',
            fontsize=10)

        self.figure.subplots_adjust(top=0.8)

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

    # Return market color as RGBA value
    def __get_market_color(self):
        if self.current_price >= self.last_closing_price:
            return [0, 0.5, 0, 1] # green
        else:
            return [1, 0, 0, 1] # red
