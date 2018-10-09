from datetime import datetime, timedelta
from robinhood.models import Market
import pandas as pd
from async_helper import async_call

MARKET = 'XNYS'

class ChartData():
    def __init__(self, portfolio, span):
        # Get current price quote concurrently in a separate thread to save time
        current_value_result = async_call(portfolio.current_value)

        market = Market.get(MARKET)
        market_timezone = market.timezone
        market_hours = market.hours()

        if market_hours.is_open:
            end_time = datetime.now()
        else:
            # Get the most recent open market hours, and change the start/end time accordingly
            market_hours = market_hours.previous_open_hours()
            end_time = market_hours.extended_closes_at

        if span <= timedelta(days=1):
            start_time = market_hours.extended_opens_at
        else:
            start_time = end_time - span

        reference_price, historical_price_map = portfolio.historical_values(start_time, end_time)

        self.name = portfolio.name

        self.market_timezone = market_timezone
        self.market_hours = market_hours

        self.series = pd.Series(historical_price_map)

        self.reference_price = reference_price
        self.current_price = current_value_result.get()
        self.updated_at = datetime.now()
        self.span = span
