import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone
from robinhood.models import Market

# Name of market to use in Robinhood
MARKET = 'XNYS'

class ChartData():
    market_timezone = None

    def __init__(self, security_name, historicals, initial_price, current_price, span=timedelta(days=1)):
        self.security_name = security_name
        self.market_hours = self.__get_market_hours()
        start_date = self.__get_start_date(span)

        time_values = []
        price_values = []
        for historical in historicals:
            # Exclude data before our requested start date
            if historical.begins_at < start_date:
                continue

            time_values.append(historical.begins_at)
            price_values.append(historical.close_price)

        self.series = pd.Series(price_values, index=time_values)
        if not initial_price:
            for price in price_values:
                if price > 0:
                    initial_price = price
                    break
        self.initial_price = initial_price
        self.current_price = current_price
        self.updated_at = datetime.now()
        self.span = span

    def get_market_timezone(self):
        if not self.__class__.market_timezone:
            self.__class__.market_timezone = timezone(Market.get(MARKET).timezone)
        return self.__class__.market_timezone

    def __get_start_date(self, span):
        start_date = datetime.now() - span
        # Get previous trading day's market hours if it is a weekend/holiday
        if start_date > self.market_hours.extended_opens_at:
            start_date = self.market_hours.extended_opens_at
        return start_date

    def __get_market_hours(self):
        market_hours = Market.hours(MARKET, datetime.now())
        if not market_hours.is_open or datetime.now() < market_hours.extended_opens_at:
            # Get market hours for the previous open day
            date = market_hours.previous_open_hours.split('/')[-2]
            market_hours = Market.hours(MARKET, date)
        return market_hours
