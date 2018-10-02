import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone

class ChartData():
    market_timezone = None

    def __init__(self, name, market_timezone, market_hours, time_price_map, reference_price, current_price, span=timedelta(days=1)):
        self.name = name

        self.market_timezone = timezone(market_timezone)
        self.market_hours = market_hours

        self.series = pd.Series(time_price_map)

        self.reference_price = reference_price
        self.current_price = current_price
        self.updated_at = datetime.now()
        self.span = span

    def get_market_timezone(self):
        return self.market_timezone
