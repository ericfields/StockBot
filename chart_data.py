from datetime import datetime, timedelta
from robinhood.models import Market
import pandas as pd

MARKET = 'XNYS'

class ChartData():
    def __init__(self, portfolio, span):
        current_price = reference_price = portfolio.cash

        market = Market.get(MARKET)
        market_timezone = market.timezone
        market_hours = market.todays_hours()

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

        historical_price_map = {}

        for asset in portfolio.assets():
            current_price += asset.current_value()
            asset_reference_price, asset_historical_items = asset.historical_values(start_time, end_time)
            reference_price += asset_reference_price * asset.weight()
            for h in asset_historical_items:
                if h.begins_at not in historical_price_map:
                    historical_price_map[h.begins_at] = portfolio.cash
                historical_price_map[h.begins_at] += h.close_price * asset.weight()

        self.name = portfolio.name

        self.market_timezone = market_timezone
        self.market_hours = market_hours

        self.series = pd.Series(historical_price_map)

        self.reference_price = reference_price
        self.current_price = current_price
        self.updated_at = datetime.now()
        self.span = span
