from django.test import TestCase, Client
from quotes.aggregator import Aggregator
from robinhood.models import *
from indexes.models import Asset, Index, User
from robinhood.stock_handler import StockHandler
from robinhood.option_handler import OptionHandler
from helpers.test_helpers import *

class QuotesTestCase(TestCase):

    def setUp(self):
        ApiResource.enable_mock = True
        mock_market()

        self.stock_handler = StockHandler()
        self.option_handler = OptionHandler()

        self.client = Client()

    def test_stock_quote(self):
        mock_stock_workflow('FAKE')
        response = self.client.get('/quotes/view/FAKE')
        self.assertEquals(200, response.status_code)

    def test_index_quote(self):
        mock_stock_workflow('FAKEA', 'FAKEB')

        index_name = 'TEST'
        create_cmd = 'create TEST FAKEA:1 FAKEB:2'

        # Ensure that the check for a preexisting stock
        # with the same name as the index is mocked
        Stock.mock_search([], symbol=index_name)

        response = self.client.post('/indexes/', {
            'user_id': 'test',
            'user_name': 'test',
            'text': create_cmd}
        )
        self.assertContains(response, 'TEST')
        self.assertContains(response, 'FAKEA')
        self.assertContains(response, 'FAKEB')

        response = self.client.get('/quotes/view/TEST')
        self.assertEquals(200, response.status_code)

    def test_empty_index_quote(self):
        Stock.mock_search([], symbol='EMPTY')
        response = self.client.post('/indexes/', {'user_id': 'test', 'user_name': 'test', 'text': 'create EMPTY'})
        self.assertContains(response, 'EMPTY')
        response = self.client.get('/quotes/view/EMPTY')
        self.assertEquals(200, response.status_code)

class AggregatorTestCase(TestCase):
    def setUp(self):
        ApiResource.enable_mocks = True
        mock_market()

        self.stock_handler = StockHandler()
        self.option_handler = OptionHandler()

        stock_identifiers = ['FAKED', 'FAKEE', 'FAKEF']
        option_identifiers = ['FAKED6P', 'FAKEE200C', 'FAKEF1800C']

        ApiResource.mock_results = {}

        mock_stock_workflow(*stock_identifiers)
        mock_option_workflow(*option_identifiers)

        self.instruments = {}
        self.instruments.update(self.stock_handler.find_instruments(*stock_identifiers))
        self.instruments.update(self.option_handler.find_instruments(*option_identifiers))

        self.test_user = User.objects.create(id='testuser')

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

    def test_quotes_with_indexes(self):
        index = Index.objects.create(user_id='testuser', name='TEST')
        [index.asset_set.create(instrument=i) for i in self.instruments.values()]
        aggregator = Aggregator(index)
        quotes = aggregator.quotes()
        self.check_all_present(quotes, index.assets())

    def check_all_present(self, results, items):
        identifiers = set()
        for i in items:
            identifiers.add(Aggregator.get_identifier(i))
        for identifier in identifiers:
            identifier = Aggregator.get_identifier(identifier)
            self.assertTrue(identifier in results)
            instrument = self.instruments[identifier]
            self.assertTrue(results[identifier].instrument == instrument.url)
