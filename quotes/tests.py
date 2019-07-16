from django.test import TestCase, Client
from quotes.aggregator import Aggregator
from robinhood.models import Instrument
from portfolios.models import Asset, Portfolio, User
from robinhood.stock_handler import StockHandler
from robinhood.option_handler import OptionHandler
from time import sleep
from datetime import datetime, timedelta

class QuotesTestCase(TestCase):

    def setUp(self):
        self.stock_handler = StockHandler()
        self.option_handler = OptionHandler()

        instruments = self.stock_handler.find_instruments('AAPL', 'MSFT', 'AMZN').values()

        user = User.objects.create(id='1234', name='testuser')
        portfolio = Portfolio.objects.create(name='QUOTESA', user_id=user.id)
        [portfolio.asset_set.create(instrument=i) for i in instruments]
        self.client = Client()

    def test_stock_quote(self):
        response = self.client.get('/quotes/view/AMZN')
        self.assertEquals(200, response.status_code)

    def test_portfolio_quote(self):
        response = self.client.post('/portfolios/', {'user_id': 'test', 'user_name': 'test', 'text': 'create TEST AAPL:1 AMZN:2'})
        self.assertContains(response, 'TEST')
        self.assertContains(response, 'AAPL')
        self.assertContains(response, 'AMZN')
        response = self.client.get('/quotes/view/TEST')
        self.assertEquals(200, response.status_code)

    def test_empty_portfolio_quote(self):
        response = self.client.post('/portfolios/', {'user_id': 'test', 'user_name': 'test', 'text': 'create EMPTY'})
        self.assertContains(response, 'EMPTY')
        response = self.client.get('/quotes/view/EMPTY')
        self.assertEquals(200, response.status_code)

class AggregatorTestCase(TestCase):
    def setUp(self):
        self.stock_handler = StockHandler()
        self.option_handler = OptionHandler()

        stock_identifiers = ['MSFT', 'AMZN', 'AAPL']
        option_identifiers = ['SNAP6P', 'AAPL200C', 'AMZN1800C']

        self.instruments = {}
        self.instruments.update(self.stock_handler.find_instruments(*stock_identifiers))
        self.instruments.update(self.option_handler.find_instruments(*option_identifiers))

        self.identifiers = stock_identifiers + option_identifiers

    def test_quotes_with_identifiers(self):
        aggregator = Aggregator(*self.identifiers)
        quotes = aggregator.quotes()
        self.check_all_present(quotes, self.identifiers)

    def test_quotes_with_instruments(self):
        aggregator = Aggregator(*self.instruments.values())
        quotes = aggregator.quotes()
        self.check_all_present(quotes, self.instruments.values())

    def test_quotes_with_assets(self):
        assets = [Asset(instrument=i) for i in self.instruments.values()]
        aggregator = Aggregator(*assets)
        quotes = aggregator.quotes()
        self.check_all_present(quotes, assets)

    def test_quotes_with_portfolios(self):
        portfolio = Portfolio.objects.create(user_id='testuser', name='TEST')
        [portfolio.asset_set.create(instrument=i) for i in self.instruments.values()]
        aggregator = Aggregator(portfolio)
        quotes = aggregator.quotes()
        self.check_all_present(quotes, portfolio.assets())

    def check_all_present(self, results, items):
        identifiers = set()
        for i in items:
            identifiers.add(Aggregator.get_identifier(i))
        for identifier in identifiers:
            identifier = Aggregator.get_identifier(identifier)
            self.assertTrue(identifier in results)
            instrument = self.instruments[identifier]
            self.assertTrue(results[identifier].instrument == instrument.url)
