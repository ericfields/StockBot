from django.test import TestCase, Client
from quotes.aggregator import quote_aggregate, historicals_aggregate
from robinhood.models import Instrument
from portfolios.models import Asset, Portfolio
from quotes.stock_handler import StockHandler
from quotes.option_handler import OptionHandler
from time import sleep
from datetime import datetime, timedelta

class QuotesTestCase(TestCase):
    def setUp(self):
        instruments = [StockHandler.search_for_instrument(s) for s in ['AAPL', 'MSFT', 'AMZN']]
        portfolio = Portfolio.objects.create(name='QUOTESA', user_id='testuser')
        [portfolio.asset_set.create(instrument=i) for i in instruments]
        self.client = Client()

    def test_portfolio_quote(self):
        pass
        #response = self.client.get("/quotes/view/{}".format('QUOTESA'))
        #self.assertEquals(200, response.status_code)

    def test_stock_quote(self):
        response = self.client.get('/quotes/view/AMZN')
        self.assertEquals(200, response.status_code)

class AggregatorTestCase(TestCase):
    def setUp(self):
        self.stock_symbols = ['MSFT', 'AMZN', 'AAPL']
        self.stocks = [StockHandler.search_for_instrument(symbol) for symbol in self.stock_symbols]

        self.option_identifiers = ['SNAP6P', 'AAPL200C', 'AMZN1800C']
        self.options = [OptionHandler.search_for_instrument(symbol) for symbol in self.option_identifiers]

        self.identifiers = self.stock_symbols + self.option_identifiers
        self.instruments = self.stocks + self.options

    def test_quotes_with_identifiers(self):
        quotes = quote_aggregate(*self.identifiers)
        self.assertEquals(len(quotes), len(self.identifiers))
        self.check_all_present(quotes)

    def test_quotes_with_instruments(self):
        quotes = quote_aggregate(*self.instruments)
        self.assertEquals(len(quotes), len(self.instruments))
        self.check_all_present(quotes)

    def test_stock_quotes_only(self):
        quotes = quote_aggregate(*self.stocks)
        self.assertEquals(len(quotes), len(self.stocks))
        for stock in self.stocks:
            self.assertTrue(stock.id in quotes)
            self.assertTrue(quotes[stock.id].symbol == stock.symbol)

    def test_quotes_with_assets(self):
        assets = [Asset(instrument=i) for i in self.instruments]
        quotes = quote_aggregate(*assets)
        self.check_all_present(quotes)

    def test_quotes_with_portfolios(self):
        portfolio = Portfolio.objects.create(user_id='testuser', name='TEST')
        [portfolio.asset_set.create(instrument=i) for i in self.instruments]
        quotes = quote_aggregate(portfolio)
        self.check_all_present(quotes)

    def test_quotes_with_duplicate_instruments(self):
        quotes = quote_aggregate(*self.instruments, *self.instruments)
        self.assertEquals(len(quotes), len(self.instruments))
        self.check_all_present(quotes)

    def test_historicals_with_identifiers(self):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        historicals = historicals_aggregate(start_date, end_date, *self.identifiers)
        self.assertEquals(len(historicals), len(self.identifiers))
        self.check_all_present(historicals)

    def check_all_present(self, results):
        self.assertEquals(len(results), len(self.instruments))
        for stock in self.stocks:
            self.assertTrue(stock.id in results)
            self.assertTrue(results[stock.id].instrument == stock.instrument_url())
        for option in self.options:
            self.assertTrue(option.id in results)
            self.assertTrue(results[option.id].instrument == option.instrument_url())
