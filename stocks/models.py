from django.db import models
from django.core.validators import MinValueValidator
import json

class User(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=14, unique=True)

    def __str__(self):
        return self.symbol

class Security(models.Model):
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

    def __str__(self):
        return "{}:{}={}".format(self.portfolio.symbol, self.identifier, self.count)
