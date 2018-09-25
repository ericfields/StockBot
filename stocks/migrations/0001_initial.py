# Generated by Django 2.1.1 on 2018-09-25 19:53

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Portfolio',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=14, unique=True)),
                ('cash', models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
            ],
        ),
        migrations.CreateModel(
            name='Security',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instrument_id', models.UUIDField(editable=False)),
                ('identifier', models.CharField(max_length=32)),
                ('count', models.FloatField(default=1, validators=[django.core.validators.MinValueValidator(0)])),
                ('type', models.CharField(choices=[('S', 'stock'), ('O', 'option')], max_length=6)),
                ('portfolio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stocks.Portfolio')),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64)),
            ],
        ),
        migrations.AddField(
            model_name='portfolio',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stocks.User'),
        ),
    ]
