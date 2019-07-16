from django.test import TestCase
from robinhood.models import *
from robinhood.stock_handler import StockHandler
from robinhood.option_handler import OptionHandler
from time import time
from helpers.cache import LongCache

class RobinhoodTestCase(TestCase):

    def setUp(self):
        self.stock_handler = StockHandler()
        self.option_handler = OptionHandler()

        self.stocks = {
            'AAPL': '450dfc6d-5510-4d40-abfb-f633b7d9be3e',
            'AMZN': 'c0bb3aec-bd1e-471e-a4f0-ca011cbec711',
            'FB': 'ebab2398-028d-4939-9f1d-13bf38f81c50',
            'GOOGL': '54db869e-f7d5-45fb-88f1-8d7072d4c8b2',
            'MSFT': '50810c35-d215-4866-9758-0ada4ac79ffa'
        }

        self.options = {
            'AAPL250.0C@01/17/20': '07030e84-540b-457e-80df-4446d9abe866',
            'AMZN1950.0P@01/15/21': '6739fdcc-e064-4dd6-8b03-decbd26b4076',
            'MSFT160.0C@12/20/19': 'e5d25111-6c7a-4873-a7db-6e1970f832e3'
        }

    def test_stock(self):
        stocks = Stock.search(symbol='AAPL')
        self.assertGreater(len(stocks), 0)
        stock = stocks[0]
        self.assertEqual('Apple', stock.short_name())

    def test_news(self):
        news = News.get('FB')
        self.assertGreater(len(news.items), 0)
        news_item = news.items[0]
        self.assertNotEqual(None, news_item.summary)

    def test_stock_handler(self):
        identifier = 'AMZN'

        instruments = self.stock_handler.find_instruments(identifier)

        self.assertTrue(identifier in instruments)
        instrument = instruments[identifier]
        self.validate_stock(identifier, instrument)

        self.assertTrue(instrument.url in instruments)
        instrument = instruments[instrument.url]
        self.validate_stock(identifier, instrument)

        # Test that the cache was set correctly
        cached_data = LongCache.get(instrument.url)
        self.assertIsNotNone(cached_data)
        instrument_from_cache = Stock(**cached_data)
        self.validate_stock(identifier, instrument_from_cache)

        cached_data = LongCache.get(Stock.search_url(symbol=instrument.symbol))
        self.assertIsNotNone(cached_data)
        self.assertTrue('results' in cached_data)
        self.assertTrue(len(cached_data['results']) == 1)
        instrument_from_cache = Stock(**cached_data['results'][0])
        self.validate_stock(identifier, instrument_from_cache)

        # Test that we retrieve from the cache correctly
        start_time = time()

        instruments = self.stock_handler.find_instruments(identifier)
        self.assertTrue(identifier in instruments)
        instrument = instruments[identifier]
        self.validate_stock(identifier, instrument)

        self.assertTrue(time() - start_time < 0.05, "LongCached entry was not used")

    def test_stock_handler_with_url(self):
        identifier = 'FB'

        url = self.get_stock_url(identifier)
        instruments = self.stock_handler.find_instruments(url)

        self.assertTrue(identifier in instruments)
        instrument = instruments[identifier]
        self.validate_stock(identifier, instrument)

        self.assertTrue(instrument.url in instruments)
        instrument = instruments[instrument.url]
        self.validate_stock(identifier, instrument)

    def test_stock_handler_multiple_stocks(self):
        instruments = self.stock_handler.find_instruments(*self.stocks.keys())
        for identifier in self.stocks:
            self.assertTrue(identifier in instruments)
            self.validate_stock(identifier, instruments[identifier])

            instrument_url = self.get_stock_url(identifier)
            self.assertTrue(instrument_url in instruments)
            self.validate_stock(identifier, instruments[instrument_url])

    def test_option_handler(self):
        identifier = 'AAPL250.0C@01/17/20'

        instruments = self.option_handler.find_instruments(identifier)

        self.assertTrue(identifier in instruments)
        instrument = instruments[identifier]
        self.validate_option(identifier, instrument)

        self.assertTrue(instrument.url in instruments)
        instrument = instruments[instrument.url]
        self.validate_option(identifier, instrument)

        # Test that the cache was set correctly
        cached_data = LongCache.get(instrument.url)
        self.assertIsNotNone(cached_data)
        instrument_from_cache = Option(**cached_data)
        self.validate_option(identifier, instrument_from_cache)

        cached_data = LongCache.get(Option.search_url(
            chain_symbol=instrument.chain_symbol,
            strike_price=instrument.strike_price,
            type=instrument.type,
            expiration_date=instrument.expiration_date
        ))
        self.assertIsNotNone(cached_data)
        self.assertTrue('results' in cached_data)
        self.assertTrue(len(cached_data['results']) > 0)

        option_data = None
        expiration_date_str = instrument.expiration_date.strftime("%Y-%m-%d")
        for d in cached_data['results']:
            if d['expiration_date'] == expiration_date_str:
                option_data = d
        self.assertIsNotNone(option_data, "No option matching expiration {} was cached".format(instrument.expiration_date))

        instrument_from_cache = Option(**option_data)
        self.validate_option(identifier, instrument_from_cache)

        # Test that we retrieve from the cache correctly
        start_time = time()

        instruments = self.option_handler.find_instruments(identifier)
        self.assertTrue(identifier in instruments)
        instrument = instruments[identifier]
        self.validate_option(identifier, instrument)

        self.assertTrue(time() - start_time < 0.05, "LongCached entry was not used")

    def test_option_handler_with_url(self):
        identifier = 'AMZN1950.0P@01/15/21'

        url = self.get_option_url(identifier)
        instruments = self.option_handler.find_instruments(url)

        self.assertTrue(identifier in instruments)
        instrument = instruments[identifier]
        self.validate_option(identifier, instrument)

        self.assertTrue(instrument.url in instruments)
        instrument = instruments[instrument.url]
        self.validate_option(identifier, instrument)

    def test_option_handler_multiple_options(self):
        instruments = self.option_handler.find_instruments(*self.options.keys())
        for identifier in self.options:
            self.assertTrue(identifier in instruments)
            self.validate_option(identifier, instruments[identifier])

            instrument_url = self.get_option_url(identifier)
            self.assertTrue(instrument_url in instruments)
            self.validate_option(identifier, instruments[instrument_url])

    def validate_stock(self, identifier, instrument):
        self.assertEquals(identifier, instrument.identifier())
        self.assertEquals(self.stocks[identifier], instrument.id)
        self.assertIsNotNone(instrument.url)

    def validate_option(self, identifier, instrument):
        self.assertEquals(identifier, instrument.identifier())
        self.assertEquals(self.options[identifier], instrument.id)
        self.assertIsNotNone(instrument.url)

    def get_stock_url(self, identifier):
        stock_id = self.stocks[identifier]
        return "https://api.robinhood.com/instruments/{}/".format(stock_id)

    def get_option_url(self, identifier):
        option_id = self.options[identifier]
        return "https://api.robinhood.com/options/instruments/{}/".format(option_id)
