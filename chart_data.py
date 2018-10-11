from datetime import datetime, timedelta
import pandas as pd
from async_helper import async_call

class ChartData():
    def __init__(self, portfolio):
        self.portfolio = portfolio

    def load(self, market_hours, span):
        now = datetime.now()

        end_time = market_hours.extended_closes_at
        if now < end_time:
            end_time = now
        if span <= timedelta(days=1):
            start_time = market_hours.extended_opens_at
        else:
            start_time = end_time - span

        # Get current price quote concurrently in a separate thread to save time
        current_value_result = async_call(self.portfolio.current_value)

        reference_price, historical_price_map = self.portfolio.historical_values(start_time, end_time)

        self.series = pd.Series(historical_price_map)

        self.name = self.portfolio.name

        self.reference_price = reference_price
        self.current_price = current_value_result.get()
        self.updated_at = now
