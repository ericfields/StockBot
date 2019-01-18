from datetime import datetime, timedelta
import pandas as pd

class ChartData():
    def __init__(self, portfolio):
        self.portfolio = portfolio

    def load(self, quotes, historicals, start_time, end_time):
        # Get current price quote concurrently in a separate thread to save time
        self.current_price = self.__portfolio_current_value(quotes)

        reference_price, historical_price_map = self.__portfolio_historical_values(historicals, start_time, end_time)

        self.series = pd.Series(historical_price_map)

        self.name = self.portfolio.name

        self.reference_price = reference_price
        self.updated_at = datetime.now()

    def __portfolio_current_value(self, quotes):
        current_value = self.portfolio.cash
        for asset in self.portfolio.assets():
            instrument_id = str(asset.instrument_id)
            if instrument_id not in quotes:
                print("Warning: no quote data exists for stock/option '{}'".format(asset.identifier))
                continue
            current_value += quotes[instrument_id].price() * asset.count * asset.unit_count()

        return current_value

    def __portfolio_historical_values(self, historicals, start_time, end_time):
        reference_price = self.portfolio.cash
        historical_price_map = {}

        for asset in self.portfolio.assets():
            instrument_id = str(asset.instrument_id)
            if instrument_id not in historicals:
                print("Warning: no historical data exists for stock/option '{}'".format(asset.identifier))
                continue

            asset_historical_data = historicals[instrument_id]
            asset_reference_price, asset_historical_items = self.__process_historicals(asset, asset_historical_data, start_time, end_time)
            reference_price += asset_reference_price * asset.count
            for h in asset_historical_items:
                if h.begins_at not in historical_price_map:
                    historical_price_map[h.begins_at] = self.portfolio.cash
                historical_price_map[h.begins_at] += h.close_price * asset.count * asset.unit_count()

        return reference_price, historical_price_map

    def __process_historicals(self, asset, historicals, start_time, end_time):
        # Filter values outside our date ranges
        while historicals.items and historicals.items[0].begins_at < start_time:
            historicals.items.pop(0)
        while historicals.items and historicals.items[-1].begins_at > end_time:
            historicals.items.pop()

        reference_price = None
        if asset.type == asset.__class__.STOCK and historicals.previous_close_price:
            reference_price = historicals.previous_close_price
        else:
            # Use the first non-zero price value
            for h in historicals.items:
                if h.open_price > 0:
                    reference_price = h.open_price
                elif h.close_price > 0:
                    reference_price = h.close_price
                if reference_price:
                    break
            if not reference_price:
                reference_price = 0

        reference_price *= asset.unit_count()
        return reference_price, historicals.items
