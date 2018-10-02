from django.db import models
from django.core.validators import MinValueValidator
import json
from robinhood.models import Stock, Option

class User(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=14, unique=True)
    cash = models.FloatField(default=0, validators=[MinValueValidator(0)])

    def __str__(self):
        return self.name

class Asset(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    instrument_id = models.UUIDField(editable=False)
    identifier = models.CharField(max_length=32)
    count = models.FloatField(default=1, validators=[MinValueValidator(0)])

    STOCK = 'S'
    OPTION = 'O'
    TYPES = (
        (STOCK, 'stock'),
        (OPTION, 'option')
    )

    type = models.CharField(max_length=6, choices=TYPES)

    def current_value(self):
        return self.instrument().current_value() * self.count

    def instrument(self):
        if self.type == self.__class__.STOCK:
            return Stock.get(self.instrument_id)
        elif self.type == self.__class__.OPTION:
            return Option.get(self.instrument_id)
        else:
            raise Exception("Cannot retrieve instrument object: No type specified for this instrument")

    def __str__(self):
        return "{}:{}={}".format(self.portfolio.name, self.identifier, self.count)
