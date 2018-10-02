from django.db import models
from django.core.validators import MinValueValidator
import json
from robinhood.models import Stock, Option, Instrument
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
                stock_endpoints.append(asset.instrument().url)
            elif asset.type == asset.__class__.OPTION:
                option_endpoints.append(asset.instrument().url)

        if stock_endpoints:
            stock_quotes = Stock.Quote.search(instruments=stock_endpoints)
        if option_endpoints:
            option_quotes = Option.Quote.search(instruments=option_endpoints)

        quote_map = {}
        for quote in stock_quotes + option_quotes:
            quote_map[quote.instrument] = quote

        for asset in self.assets():
            quote = quote_map[asset.instrument().url]
            total_value += quote.price() * asset.weight()

        return total_value


    def historical_values(self, start_date, end_date):
        historical_price_map = {}
        reference_price = self.cash

        # Make a single query for all historicals for each data type
        stock_endpoints = []
        option_endpoints = []
        stock_historicals = []
        option_historicals = []
        for asset in self.assets():
            if asset.type == asset.__class__.STOCK:
                stock_endpoints.append(asset.instrument().url)
            elif asset.type == asset.__class__.OPTION:
                option_endpoints.append(asset.instrument().url)

        historical_params = Instrument.historical_params(start_date, end_date)

        if stock_endpoints:
            stock_historicals = Stock.Historicals.search(instruments=stock_endpoints, **historical_params)
        if option_endpoints:
            option_historicals = Option.Historicals.search(instruments=option_endpoints, **historical_params)

        historicals_map = {}
        for historicals in stock_historicals + option_historicals:
            historicals_map[historicals.instrument] = historicals

        for asset in self.assets():
            historicals = historicals_map[asset.instrument().url]
            asset_reference_price, asset_historical_items = self.__process_historicals(asset, historicals, start_date, end_date)
            reference_price += asset_reference_price * asset.weight()
            for h in asset_historical_items:
                if h.begins_at not in historical_price_map:
                    historical_price_map[h.begins_at] = self.cash
                historical_price_map[h.begins_at] += h.close_price * asset.weight()

        return reference_price, historical_price_map


    def __process_historicals(self, asset, historicals, start_date, end_date = datetime.now()):
        if asset.date_bought and start_date < asset.date_bought:
            start_date = asset.date_bought
        if asset.date_sold and end_date > asset.date_sold:
            end_date = asset.date_sold

        # Filter values outside our date ranges
        while historicals.items[0].begins_at < start_date:
            historicals.items.pop(0)
        while historicals.items[-1].begins_at > end_date:
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

        return reference_price, historicals.items

    def __str__(self):
        return self.name

    def value(self):
        return self.cash + sum([a.current_value() for a in self.asset_set.all()])

class Asset(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    instrument_id = models.UUIDField(editable=False)
    identifier = models.CharField(max_length=32)
    count = models.FloatField(default=1, validators=[MinValueValidator(0)])

    date_bought = models.DateTimeField(null=True)
    date_sold = models.DateTimeField(null=True)

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
            kwargs['identifier'] = instrument.identifier()
            if isinstance(instrument, Stock):
                kwargs['type'] = self.__class__.STOCK
            elif isinstance(instrument, Option):
                kwargs['type'] = self.__class__.OPTION
            else:
                raise Exception("Unrecognized instrument type: {}".format(instrument.__class__))
            self.instrument_object = instrument

        super().__init__(*args, **kwargs)

    def current_value(self):
        return self.instrument().current_value() * self.weight()

    def weight(self):
        w = self.count
        if self.type == self.__class__.OPTION:
            # The returned value should be that of a single option contract for the stock,
            # i.e. that of a contract for 100 shares
            w *= 100
        return w

    def instrument(self):
        if not self.instrument_object:
            if self.type == self.__class__.STOCK:
                self.instrument_object = Stock.get(self.instrument_id)
            elif self.type == self.__class__.OPTION:
                self.instrument_object = Option.get(self.instrument_id)
            else:
                raise Exception("Cannot retrieve instrument object: No type specified for this instrument")
        return self.instrument_object

    def __str__(self):
        return "{}:{}={}".format(self.portfolio.name, self.identifier, self.count)
