import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone

class ChartData():
    market_timezone = None

    def __init__(self, security_name, market_timezone, market_hours, time_price_map, initial_price, current_price, span=timedelta(days=1)):
        self.security_name = security_name

        self.market_timezone = timezone(market_timezone)
        self.market_hours = market_hours

        self.series = pd.Series(time_price_map)

        self.initial_price = initial_price
        self.current_price = current_price
        self.updated_at = datetime.now()
        self.span = span

    def get_market_timezone(self):
        return self.market_timezone
