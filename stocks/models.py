from django.db import models

# Create your models here.
class Stock(models.Model):
    symbol = models.CharField(max_length=5, primary_key=True)
    company_name = models.CharField(max_length=100)
