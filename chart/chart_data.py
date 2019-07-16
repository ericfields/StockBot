from datetime import datetime, timedelta
import pandas as pd
from collections import OrderedDict

import logging
logger = logging.getLogger('stockbot')

class ChartData():

    def __init__(self, portfolio):
        self.portfolio = portfolio

    def load(self, quotes, historicals, start_time, end_time):
        self.name = self.portfolio.name

        # Remove any assets without historical data, i.e. missing or delisted assets
        assets = []
        for asset in self.portfolio.assets():
            if asset.instrument_url in historicals:
                assets.append(asset)
            elif asset.instrument_url in quotes:
                logger.info("'{}' has likely been bought out or acquired. Treating as cash.".format(asset.identifier))
                self.portfolio.cash += quotes[asset.instrument_url].price() * asset.count * asset.unit_count()
            else:
                logger.warning("No data exists for stock/option '{}'".format(asset.identifier))

        # Get current price quote concurrently in a separate thread to save time
        self.current_price = self.__get_portfolio_current_value(assets, quotes)

        self.reference_price = self.__get_reference_price(assets, historicals)

        chart_price_map = self.__get_chart_price_map(assets, historicals, start_time, end_time)
        self.series = pd.Series(chart_price_map)

        self.updated_at = datetime.now()

    def __get_portfolio_current_value(self, assets, quotes):
        current_value = self.portfolio.cash
        for asset in assets:
            asset_quote = quotes[asset.instrument_url]
            current_value += asset_quote.price() * asset.count * asset.unit_count()

        return current_value

    def __get_reference_price(self, assets, historicals):
        reference_price = self.portfolio.cash

        for asset in assets:
            asset_historicals = historicals[asset.instrument_url]
            if asset.type == asset.__class__.STOCK and asset_historicals.previous_close_price:
                asset_reference_price = asset_historicals.previous_close_price
            else:
                asset_reference_price = 0
                # Use the first non-zero price value
                for h in asset_historicals.items:
                    if h.open_price > 0:
                        asset_reference_price = h.open_price
                    elif h.close_price > 0:
                        asset_reference_price = h.close_price
                    if asset_reference_price:
                        break

            reference_price += asset_reference_price * asset.count * asset.unit_count()


        return reference_price

    def __get_chart_price_map(self, assets, historicals, start_time, end_time):
        chart_price_map = {}
        for asset in assets:
            asset_historicals = historicals[asset.instrument_url]
            for h in asset_historicals.items:
                if start_time <= h.begins_at <= end_time:
                    if h.begins_at not in chart_price_map:
                        chart_price_map[h.begins_at] = self.portfolio.cash
                    chart_price_map[h.begins_at] += h.close_price * asset.count * asset.unit_count()
        return chart_price_map
