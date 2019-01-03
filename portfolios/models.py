from django.db import models
from django.core.validators import MinValueValidator
import json
from robinhood.models import Stock, Option, Instrument
from helpers.async_helper import async_call
from datetime import datetime

class User(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=14, unique=True)
    cash = models.FloatField(default=0, validators=[MinValueValidator(0)])

    def __init__(self, *args, **kwargs):
        self.tmp_assets = []
        super().__init__(*args, **kwargs)

    def add_asset(self, asset):
        self.tmp_assets.append(asset)

    def assets(self):
        if self.pk:
            return self.asset_set.all()
        else:
            return self.tmp_assets

    def current_value(self):
        total_value = self.cash

        stock_endpoints = []
        option_endpoints = []
        stock_quotes = []
        option_quotes = []
        for asset in self.assets():
            if asset.type == asset.__class__.STOCK:
                stock_endpoints.append(asset.instrument_url)
            elif asset.type == asset.__class__.OPTION:
                option_endpoints.append(asset.instrument_url)

        quote_results = []
        if stock_endpoints:
            quote_results.append(async_call(Stock.Quote.search, instruments=stock_endpoints))
        if option_endpoints:
            quote_results.append(async_call(Option.Quote.search, instruments=option_endpoints))

        instrument_quotes = []
        for result in quote_results:
            instrument_quotes += result.get()
        quote_map = {}
        for quote in instrument_quotes:
            quote_map[quote.instrument] = quote

        for asset in self.assets():
            try:
                quote = quote_map[asset.instrument_url]
            except KeyError:
                # This stock's data is missing from Robinhood. It is likelyi that the company was acquired or delisted.
                # It should be removed from the user's portfolio.
                print("WARN: Asset no longer exists in Robinhood: {}".format(asset.identifier))
                continue
            total_value += quote.price() * asset.count * asset.unit_count()

        return total_value

    def historical_values(self, start_date, end_date):
        historical_price_map = {}
        reference_price = self.cash

        # Make a single query for all historicals for each data type
        stock_endpoints = []
        option_endpoints = []
        for asset in self.assets():
            if asset.type == Asset.STOCK:
                stock_endpoints.append(asset.instrument_url)
            elif asset.type == Asset.OPTION:
                option_endpoints.append(asset.instrument_url)

        historical_params = Instrument.historical_params(start_date, end_date)

        historicals_results = []
        if stock_endpoints:
            historicals_results.append(async_call(Stock.Historicals.search, instruments=stock_endpoints, **historical_params))
        if option_endpoints:
            historicals_results.append(async_call(Option.Historicals.search, instruments=option_endpoints, **historical_params))

        instrument_historicals = []
        for result in historicals_results:
            instrument_historicals += result.get()

        historicals_map = {}
        for historicals in instrument_historicals:
            historicals_map[historicals.instrument] = historicals

        for asset in self.assets():
            try:
                historicals = historicals_map[asset.instrument_url]
            except KeyError:
                # This stock's data is missing from Robinhood. It is likelyi that the company was acquired or delisted.
                # It should be removed from the user's portfolio.
                print("WARN: Asset no longer exists in Robinhood: {}".format(asset.identifier))
                continue
            asset_reference_price, asset_historical_items = self.__process_historicals(asset, historicals, start_date, end_date)
            reference_price += asset_reference_price * asset.count
            for h in asset_historical_items:
                if h.begins_at not in historical_price_map:
                    historical_price_map[h.begins_at] = self.cash
                historical_price_map[h.begins_at] += h.close_price * asset.count * asset.unit_count()

        return reference_price, historical_price_map


    def __process_historicals(self, asset, historicals, start_date, end_date = datetime.now()):
        # Filter values outside our date ranges
        while historicals.items and historicals.items[0].begins_at < start_date:
            historicals.items.pop(0)
        while historicals.items and historicals.items[-1].begins_at > end_date:
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

        reference_price *= asset.unit_count()
        return reference_price, historicals.items

    def __str__(self):
        return self.name

    def value(self):
        return self.cash + sum([a.current_value() for a in self.asset_set.all()])

class Asset(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    instrument_id = models.UUIDField(null=True)
    instrument_url = models.CharField(max_length=160, null=True)
    identifier = models.CharField(max_length=32)
    count = models.FloatField(default=1, validators=[MinValueValidator(0)])

    date_acquired = models.DateTimeField(null=True)
    date_released = models.DateTimeField(null=True)

    instrument_object = None

    STOCK = 'S'
    OPTION = 'O'
    TYPES = (
        (STOCK, 'stock'),
        (OPTION, 'option')
    )

    type = models.CharField(max_length=6, choices=TYPES)

    def __init__(self, *args, **kwargs):
        # Extract instrument object into component fields
        if 'instrument' in kwargs:
            instrument = kwargs['instrument']
            del kwargs['instrument']
            kwargs['instrument_id'] = instrument.id
            kwargs['instrument_url'] = instrument.url
            kwargs['identifier'] = instrument.identifier()
            if isinstance(instrument, Stock):
                kwargs['type'] = self.__class__.STOCK
            elif isinstance(instrument, Option):
                kwargs['type'] = self.__class__.OPTION
            else:
                raise Exception("Unrecognized instrument type: {}".format(instrument.__class__))
            self.instrument_object = instrument

        super().__init__(*args, **kwargs)

    def current_value(self, adjusted_count = None):
        count = adjusted_count or self.count
        quote = self.__instrument_class().Quote.get(self.instrument_id)
        if not quote:
            # Asset likely no longer exists
            return 0
        return quote.price() * self.unit_count() * count

    def unit_count(self):
        if self.type == self.__class__.OPTION:
            return 100
        else:
            return 1

    def instrument(self):
        if not self.instrument_object:
            self.instrument_object = self.__instrument_class().get(self.instrument_url)

        return self.instrument_object

    def __instrument_class(self):
        if self.type == self.__class__.STOCK:
            return Stock
        elif self.type == self.__class__.OPTION:
            return Option
        else:
            raise Exception("Cannot determine instrument class: No type specified for this instrument")

    def __str__(self):
        return "{}:{}={}".format(self.portfolio.name, self.identifier, self.count)
