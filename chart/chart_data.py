import pandas as pd

from indexes.models import Asset

import logging
logger = logging.getLogger('stockbot')

class ChartData():
    name: str
    identifier: str
    assets: list[Asset]

    def __init__(self, name: str, identifier: str, assets: list[Asset]):
        self.name = name
        self.identifier = identifier
        self.assets = assets

    def load(self, quotes, historicals, start_time, end_time):
        # Remove any assets without historical data, i.e. missing or delisted assets
        valid_assets = []
        for asset in self.assets:
            if asset.instrument_url in historicals:
                valid_assets.append(asset)
            elif asset.instrument_url in quotes:
                logger.info("'{}' has likely been bought out or acquired, ignoring.".format(asset.identifier))
            else:
                logger.warning("No data exists for stock/option '{}'".format(asset.identifier))

        # Get current price quote concurrently in a separate thread to save time
        self.current_price = self.__get_index_current_value(valid_assets, quotes)

        self.reference_price = self.__get_reference_price(valid_assets, historicals, start_time)

        chart_price_map = self.__get_chart_price_map(valid_assets, historicals, start_time, end_time)
        self.series = pd.Series(chart_price_map)

    def __get_index_current_value(self, assets, quotes):
        current_value = 0
        for asset in assets:
            if asset.instrument_url in quotes:
                asset_quote = quotes[asset.instrument_url]
                # If this is an expired option, it will have a quoted value of zero.
                # However, it may have expired in the money, in which case Robinhood
                # will have sold it and converted it to cash. Use its last quoted value
                # as the current value instead for better accuracy.
                if asset.type == asset.OPTION and asset_quote.price() == 0:
                    asset_current_value = asset_quote.previous_close_price
                else:
                    asset_current_value = asset_quote.price()
                current_value += asset_current_value * asset.count * asset.unit_count()

        return current_value

    def __get_reference_price(self, assets, historicals, start_time):
        reference_price = 0

        for asset in assets:
            asset_historicals = historicals[asset.instrument_url]
            if asset.type == asset.__class__.STOCK and asset_historicals.previous_close_price:
                asset_reference_price = asset_historicals.previous_close_price
            else:
                asset_reference_price = 0
                # Use the first non-zero price value
                for h in asset_historicals.items:
                    if h.begins_at >= start_time:
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
                # Check if the option is expired at this time
                if start_time <= h.begins_at <= end_time:
                    if h.begins_at not in chart_price_map:
                        chart_price_map[h.begins_at] = 0

                    chart_price_map[h.begins_at] += h.close_price * asset.count * asset.unit_count()
        return chart_price_map
