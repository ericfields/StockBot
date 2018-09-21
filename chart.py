import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from io import BytesIO

class Chart():
    # Size of the overall chart
    size = (7, 3)

    # Colored areas indicating non-trading hours for day chart
    after_hours_tint = {'facecolor': 'grey', 'alpha': 0.1}

    title_layout = {'horizontalalignment': 'left', 'x': 0.0, 'y': 1.15}
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

    def __init__(self, chart_data, hide_value = False):
        self.market_timezone = chart_data.get_market_timezone()
        self.market_hours = chart_data.market_hours

        self.series = chart_data.series
        self.initial_price = chart_data.initial_price
        self.current_price = chart_data.current_price
        self.updated_at = chart_data.updated_at

        self.title = chart_data.security_name

        self.span = chart_data.span

        self.figure, self.axis = plt.subplots(1, figsize=self.size)

        # Add current price to graph
        if datetime.now() > self.market_hours.extended_closes_at:
            # Showing the actual current quote time on an after-hours graph
            # causes ugliness. Fake the time for the last datapoint instead.
            last_graph_time = self.series.index[-1] + timedelta(minutes=5)
        else:
            last_graph_time = self.updated_at

        self.series.at[last_graph_time] = self.current_price
        self.axis.set_xlim(right=last_graph_time)

        timespan = self.__get_timespan()

        # Week charts are ugly due to gaps in after-hours/weekend trading activity.
        # Re-index these graphs in a way that hides the gaps (at the cost of time accuracy)
        if timedelta(days=1) < timespan < timedelta(weeks=2):
            self.__normalize_indices()

        self.__show_title()

        self.axis.xaxis_date(self.market_timezone)

        self.axis.set_xlim(left=self.series.index[0])

        # Format chart depending on data time span
        if timespan <= timedelta(days=1):
            time_format = self.hourly_format
            self.__show_day_chart_options()
        elif timespan <= timedelta(days=120):
            time_format = self.daily_format
        elif timespan <= timedelta(days=365*3):
            time_format = self.monthly_format
        else:
            time_format = self.yearly_format
            # Set ticks so that years aren't duplicated
            year_ticks = []
            prev_time = None
            for time in self.series.index:
                time = time.replace(tzinfo=self.market_timezone)
                if prev_time and time.year > prev_time.year:
                    year_ticks.append(time)
                prev_time = time
            self.axis.set_xticks(year_ticks)

        self.axis.xaxis.set_major_formatter(
            mdates.DateFormatter(time_format, self.market_timezone)
        )

        self.axis.margins(self.margins)
        self.axis.grid(self.show_grid, **self.grid_style)

        self.__show_price_info(hide_value)

        self.__show_chart_info()

        self.figure.subplots_adjust(top=self.top_spacing)

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
        if len(self.title) > self.max_title_length:
            self.title = self.title[0:self.max_title_length] + '...'

        # Dollar signs do weird things in the title text view, escape them
        title = self.title.replace('$', "\$")
        self.axis.set_title(title, **self.title_layout)

    def __show_price_info(self, hide_value = False):
        # Show the graph as green if the stock's up, or red if it's down
        market_color = self.__get_market_color()

        if not hide_value:
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

        price_change_str = ""
        if not hide_value:
            price_change_str += "{}{} ".format(change_sign, point_change)
        price_change_str += "({}%)".format(percentage_change)
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

    def __show_chart_info(self):
        # Show the date/time info
        span_str = self.__get_timespan_str()
        date_str = datetime.now(self.market_timezone).strftime(
            self.chart_time_str_format)
        info_str = span_str + "\n" + date_str

        self.axis.text(self.chart_time_pos[0], self.chart_time_pos[1], info_str,
            transform=plt.gcf().transFigure,
            color = 'grey',
            fontsize=10)

    # Get a string representing the duration of the graph
    # Some rounding is done to keep the string "pretty"
    # and to account for weekends, holidays, etc.
    def __get_timespan_str(self):
        days = self.__get_timespan() / timedelta(days=1)

        unit = None
        num = None

        if days <= 1:
            return 'Daily'
        else:
            unit_days = {
                'year': 365,
                'month': 30
            }
            for u in unit_days:
                # Determine how far off we are from the current unit
                ud = unit_days[u]
                offset = Chart.offset(days, ud)
                if offset < 0.1:
                    unit = u
                    num = round(days / unit_days[u])
                    break

            if not unit:
                unit = 'day'
                num = days

        str = "{} {}".format(int(num), unit)
        if num > 1:
            str += 's'
        return str

    def offset(value, increment):
        if value > increment:
            overage = value % increment
            if overage == 0:
                return 0
            lower_diff = overage
            upper_diff = increment - overage
            return min(lower_diff, upper_diff) / increment
        else:
            return (increment - value) / increment

    # Return timespan of graph data, to the nearest day
    def __get_timespan(self):
        if len(self.series) > 1:
            td = self.series.index[-1] - self.series.index[0]
            # Round to the nearest day
            approx_days = round(td / timedelta(days=1))
            return timedelta(days=approx_days)
        else:
            return timedelta(0)

    # Return graph color depending on whether price is up or down
    def __get_market_color(self):
        if self.current_price >= self.initial_price:
            return self.positive_market_color
        else:
            return self.negative_market_color
