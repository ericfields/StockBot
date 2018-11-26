import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from io import BytesIO
from robinhood.models import Market
from enum import Enum
from collections import OrderedDict
from async_helper import async_call

MARKET = 'XNYS'

class Chart():
    # Size of the overall chart
    size = (7, 3)

    # Colored areas indicating non-trading hours for day chart
    after_hours_tint = {'facecolor': 'grey', 'alpha': 0.1}

    title_layout = {'horizontalalignment': 'left', 'x': 0.0, 'y': 1.15}
    max_title_length = 64

    # Style for line indicating the opening price
    reference_price_line_style = {'linestyle': 'dotted', 'color': 'grey'}

    # Colors for plot lines.
    # Color is defined as an RGBA value (red, green, blue, alpha)
    class Color(Enum):
        GREEN = [0, 0.5, 0, 1]
        LIGHT_GREEN = [0, 0.85, 0, 1]
        LIME_GREEN = [0, 1, 0, 1]
        LIGHT_BLUE = [0, 1, 1, 1]
        BLUE = [0, 0.5, 1, 1]

        RED = [1, 0, 0, 1]
        BLOOD_ORANGE = [1, 0.25, 0, 1]
        ORANGE = [1, 0.5, 0, 1]
        TANGERINE = [1, 0.75, 0, 1]
        YELLOW = [1, 1, 0, 1]

        POSITIVE_COLORS = [GREEN, LIGHT_GREEN, LIME_GREEN, LIGHT_BLUE, BLUE]
        NEGATIVE_COLORS = [RED, BLOOD_ORANGE, ORANGE, TANGERINE, YELLOW]

    class Pattern(Enum):
        SOLID = (0, ())
        DASHED = (0, (5, 1))
        DOTTED = (0, (1, 1))

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

    def __init__(self, title, span, hide_value = False):
        market = Market.get(MARKET)
        self.market_timezone = market.timezone

        self.now = datetime.now()
        self.now_with_tz = datetime.now(self.market_timezone)

        market_hours = market.hours()
        if not (market_hours.is_open and self.now >= market_hours.extended_opens_at):
            # Get the most recent open market hours, and change the start/end time accordingly
            market_hours = market_hours.previous_open_hours()
        self.market_hours = market_hours

        self.span = span
        self.hide_value = hide_value

        self.figure, self.axis = plt.subplots(1, figsize=self.size)

        self.__show_title(title)
        self.__show_chart_metadata()

        self.axis.xaxis_date(self.market_timezone)

        self.start_time = None
        self.end_time = self.market_hours.extended_closes_at

        self.axis.margins(self.margins)
        self.axis.grid(self.show_grid, **self.grid_style)
        self.figure.subplots_adjust(top=self.top_spacing)

        self.axis.set_xlim(right=self.end_time)
        self.__set_time_format()

        if self.hide_value:
            self.axis.yaxis.set_major_formatter(FuncFormatter(self.__percent))

    def plot(self, *chart_data_sets):
        # Load all the chart data sets asynchronously to save time
        async_results = []
        for chart_data in chart_data_sets:
            async_results.append(async_call(chart_data.load, self.market_hours, self.span))
        [ar.get() for ar in async_results]

        chart_data_sets = sorted(chart_data_sets, key=self.__sort_by_gain, reverse=True)

        single_set = len(chart_data_sets) == 1

        if not single_set:
            if self.__is_day_chart():
                # Add a dashed line indicating the opening price
                self.axis.axhline(1.0,
                    **self.reference_price_line_style)
            if not self.hide_value:
                self.hide_value = True
                self.axis.yaxis.set_major_formatter(FuncFormatter(self.__percent))

        colors, patterns = self.__get_line_styles(chart_data_sets)
        style_index = 0

        for chart_data in chart_data_sets:
            series = chart_data.series
            current_price = chart_data.current_price
            reference_price = chart_data.reference_price

            # Add the current price to the graph
            if self.now <= self.market_hours.extended_closes_at:
                series.at[self.now] = current_price
            else:
                series.at[self.end_time] = current_price

            # Week charts are ugly due to gaps in after-hours/weekend trading activity.
            # Re-index these graphs in a way that hides the gaps (at the cost of time accuracy)
            if timedelta(days=1) < self.span < timedelta(weeks=2):
                series = self.__normalize_indices(series)

            if self.hide_value:
                # Do not show the actual dollar values. Only show as percentages.
                for t in series.index:
                    series.at[t] = series.at[t] / reference_price
                current_price /= reference_price
                reference_price = 1.0

            if single_set:
                # Show the price info for the single data set
                self.__show_price_info(current_price, reference_price)

            # See if we need to adjust the date range
            if not self.start_time or self.start_time > series.index[0]:
                self.start_time = series.index[0]
                self.axis.set_xlim(left=self.start_time)

            line_color = colors[style_index]
            line_pattern = patterns[style_index]
            style_index += 1

            label = "{} ({:0.1f}%)".format(chart_data.name, (current_price - 1) * 100)

            self.axis.plot(series,
                color=line_color,
                linestyle=line_pattern,
                label=label)


        if not single_set:
            self.axis.legend()

    def __sort_by_gain(self, chart_data):
        return chart_data.current_price / chart_data.reference_price

    def __get_line_styles(self, chart_data_sets):
        pattern_list = list(p.value for p in Chart.Pattern)

        positive_color_list = Chart.Color.POSITIVE_COLORS.value
        positive_colors = []
        positive_patterns = []
        color_index = 0
        pattern_index = 0

        for chart_data in chart_data_sets:
            price_change = chart_data.current_price / chart_data.reference_price
            if price_change < 1.0:
                break
            positive_colors.append(positive_color_list[color_index])
            positive_patterns.append(pattern_list[pattern_index])

            pattern_index += 1
            if pattern_index >= len(pattern_list):
                pattern_index = 0
                color_index += 1

        negative_color_list = Chart.Color.NEGATIVE_COLORS.value
        negative_colors = []
        negative_patterns = []
        color_index = 0
        pattern_index = 0

        for chart_data in reversed(chart_data_sets):
            price_change = chart_data.current_price / chart_data.reference_price
            if price_change >= 1.0:
                break
            negative_colors.append(negative_color_list[color_index])
            negative_patterns.append(pattern_list[pattern_index])

            pattern_index += 1
            if pattern_index >= len(pattern_list):
                pattern_index = 0
                color_index += 1

        colors = positive_colors + list(reversed(negative_colors))
        patterns = positive_patterns + list(reversed(negative_patterns))
        return colors, patterns



    def get_img_data(self):
        figure_img_data = BytesIO()
        self.figure.savefig(figure_img_data, format='png', dpi=(100))
        plt.close(self.figure)

        return figure_img_data.getvalue()

    def __next_linestyle(self):
        linestyle = self.remaining_line_patterns.pop(0)
        return linestyle[1]

    def __percent(self, y, pos):
        return '{}%'.format(round((y - 1) * 100, 2))

    def __normalize_indices(self, series):
        new_index = []
        new_date = series.index[0]
        time_diff = (series.index[-1] - series.index[0]).total_seconds()
        spread_factor = time_diff / len(series.index)
        for n in range(0, len(series.index)):
            new_date += timedelta(seconds=spread_factor)
            new_index.append(new_date)
        return pd.Series(series.values, index=new_index)

    def __show_title(self, title):
        if len(title) > self.max_title_length:
            title = title[0:self.max_title_length] + '...'

        # Dollar signs do weird things in the title text view, escape them
        title = title.replace('$', "\$")
        self.axis.set_title(title, **self.title_layout)

    def __show_price_info(self, current_price, reference_price):
        if current_price >= reference_price:
            market_color = Chart.Color.GREEN
        else:
            market_color = Chart.Color.RED

        if self.__is_day_chart():
            # Add a dashed line indicating the opening price
            self.axis.axhline(reference_price,
                **self.reference_price_line_style)

        if not self.hide_value:
            if current_price < 0.1:
                self.current_price_str = '${:,.4f}'.format(current_price)
            else:
                self.current_price_str = '${:,.2f}'.format(current_price)
            self.axis.text(self.current_price_xpos, self.price_info_height, self.current_price_str,
                transform=plt.gcf().transFigure,
                fontsize=self.current_price_fontsize)

        # Show the latest price/change on the graph
        price_change = current_price - reference_price
        if price_change >= 0:
            change_sign = '+'
        else:
            change_sign = '-'
        percentage_change = round(price_change / reference_price * 100, 2)

        if current_price < 0.1:
            point_change = round(abs(price_change), 4)
        else:
            point_change = round(abs(price_change), 2)

        price_change_str = ""
        if not self.hide_value:
            price_change_str += "{}{} ".format(change_sign, point_change)
        price_change_str += "({}%)".format(percentage_change)
        self.axis.text(self.price_change_xpos, self.price_info_height, price_change_str,
            transform=plt.gcf().transFigure,
            color = market_color.value,
            fontsize=self.price_change_fontsize)

    # Format chart depending on time span
    def __set_time_format(self):
        if self.__is_day_chart():
            time_format = self.hourly_format
            self.__show_day_chart_options()
        elif self.span <= timedelta(days=120):
            time_format = self.daily_format
        elif self.span <= timedelta(days=365*3):
            time_format = self.monthly_format
        else:
            time_format = self.yearly_format
            # Set ticks so that years aren't duplicated
            year_ticks = []
            year = self.end_time.year
            while year >= (self.end_time - self.span).year:
                year_ticks.insert(0, pd.Timestamp(year=year, month=1, day=1, tz=self.market_timezone))
                year -= 1
            self.axis.set_xticks(year_ticks)

        self.axis.xaxis.set_major_formatter(
            mdates.DateFormatter(time_format, self.market_timezone)
        )

    def __show_day_chart_options(self):
        # Indicate times outside trading hours
        opens_at = self.market_hours.opens_at
        extended_opens_at = self.market_hours.extended_opens_at
        closes_at = self.market_hours.closes_at
        extended_closes_at = self.market_hours.extended_closes_at

        self.axis.axvspan(extended_opens_at, opens_at,
            **self.after_hours_tint)

        self.axis.axvspan(extended_closes_at, closes_at,
            **self.after_hours_tint)

    def __show_chart_metadata(self):
        # Show the date/time info
        span_str = self.__get_timespan_str()
        date_str = self.now_with_tz.strftime(
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
        days = self.span / timedelta(days=1)

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

    # Determine whether or not this is a day chart
    def __is_day_chart(self):
        return self.span <= timedelta(days=1)
