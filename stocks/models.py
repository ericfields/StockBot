from django.db import models
from django.core.validators import MinValueValidator
import json

# Custom field type for storing JSON fields to enable storing dicts, lists, etc.
class JSONField(models.Field):
    # Deserialization
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return json.loads(value)

    def to_python(self, value):
        if isinstance(value, dict):
            return value

        if value is None:
            return {}

        if isinstance(value, str):
            return json.loads(value)

    def get_prep_value(self, value):
        return json.dumps(value)

class User(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(primary_key=True, max_length=14)

    def __str__(self):
        return self.symbol

class Security(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    instrument_id = models.UUIDField(editable=False)
    name = models.CharField(max_length=32)
    count = models.FloatField(default=1, validators=[MinValueValidator(0)])

    STOCK = 'S'
    OPTION = 'O'
    TYPES = (
        (STOCK, 'stock'),
        (OPTION, 'option')
    )

    type = models.CharField(max_length=6, choices=TYPES)

    def unique_name(self):
        return "{}:{}".format(self.portfolio.symbol, self.name)

    class Meta:
        unique_together = ('portfolio', 'name')

    def __str__(self):
        return "{}:{}".format(self.portfolio_id, self.name)
