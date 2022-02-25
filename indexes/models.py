from django.db import models
from django.core.validators import MinValueValidator
from robinhood.models import Stock, Option

class User(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

class Index(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=14, unique=True)

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

    def __str__(self):
        return self.name

class Asset(models.Model):
    id = models.AutoField(primary_key=True)
    index = models.ForeignKey(Index, on_delete=models.CASCADE)
    instrument_id = models.UUIDField(null=True)
    instrument_url = models.CharField(max_length=160, null=True)
    identifier = models.CharField(max_length=32)
    count = models.FloatField(default=1, validators=[MinValueValidator(0)])

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
            kwargs['instrument_url'] = instrument.instrument_url()
            kwargs['identifier'] = instrument.identifier()
            if isinstance(instrument, Stock):
                kwargs['type'] = self.__class__.STOCK
            elif isinstance(instrument, Option):
                kwargs['type'] = self.__class__.OPTION
            else:
                raise Exception("Unrecognized instrument type: {}".format(instrument.__class__))
            self.instrument_object = instrument

        super().__init__(*args, **kwargs)

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
        return "{}:{}={}".format(self.index.name, self.identifier, self.count)
