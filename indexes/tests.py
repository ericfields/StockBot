from django.test import TestCase, Client
import string
import random
from django.conf import settings
from helpers.test_helpers import *
from robinhood.models import Stock

class IndexViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()


    def test_create_index(self):
        mock_stock_workflow('AAPL', 'AMZN')
        name, response = self.create_index('bob', 'AAPL AMZN:2')
        self.assertContains(response, name)
        self.assertContains(response, 'AAPL')
        self.assertContains(response, 'AMZN')

    def test_display_index(self):
        mock_stock_workflow('AAPL', 'AMZN')
        name, response = self.create_index('bob', 'AAPL AMZN:2')
        self.assertEqual(200, response.status_code)
        response = self.display_index('bob', name)
        self.assertContains(response, name)
        self.assertContains(response, 'AAPL')
        self.assertContains(response, 'AMZN')

        # Test lowercase as well
        response = self.display_index('bob', name.lower())
        self.assertContains(response, name)
        self.assertContains(response, 'AAPL')
        self.assertContains(response, 'AMZN')

    def test_create_multiple_indexes(self):
        mock_stock_workflow('AAPL', 'AMZN')
        name, response = self.create_index('bob', 'AAPL:3 AMZN:4')
        self.assertContains(response, name)
        self.assertContains(response, 'AAPL')
        self.assertContains(response, 'AMZN')
        name, response = self.create_index('bob', 'AAPL:5 AMZN:6')
        self.assertContains(response, name)
        self.assertContains(response, 'AAPL')
        self.assertContains(response, 'AMZN')

    def test_list_multiple_indexes(self):
        mock_stock_workflow('AAPL', 'AMZN')
        name1, _ = self.create_index('bob', 'AAPL:1 AMZN:2')
        name2, _ = self.create_index('bob', 'AAPL:3 AMZN:4')

        response = self.display_index('bob')
        self.assertContains(response, 'You have multiple indexes.')
        self.assertContains(response, name1)
        self.assertContains(response, name2)

        response = self.display_index('bob', name1)
        self.assertContains(response, name1)
        response = self.display_index('bob', name2)
        self.assertContains(response, name2)

    def test_index_privacy(self):
        mock_stock_workflow('AAPL', 'AMZN')
        bobs, _ = self.create_index('bob', 'AAPL:1 AMZN:2')
        alices, _ = self.create_index('alice', 'AAPL:3 AMZN:4')

        response = self.display_index('bob', bobs)
        self.assertContains(response, bobs)
        self.assertNotContains(response, alices)
        response = self.display_index('alice', alices)
        self.assertContains(response, alices)
        self.assertNotContains(response, bobs)

    def test_index_add(self):
        mock_stock_workflow('AAPL', 'AMZN')
        name, response = self.create_index('bob')
        self.assertContains(response, name)

        response = self.index_add('bob', 'AAPL AMZN:2')
        self.assertContains(response, 'AAPL')
        self.assertContains(response, 'AMZN')

        mock_stock_workflow('AAPL', 'AMZN', 'MSFT')
        response = self.index_add('bob', 'MSFT', name)
        self.assertContains(response, name)
        self.assertContains(response, 'MSFT')
        self.assertContains(response, 'AAPL')
        self.assertContains(response, 'AMZN')

    def test_invalid_index_or_cmd(self):
        response = self.display_index('bob', 'nonexistent')
        self.assertContains(response, "Unknown command or index: 'nonexistent'")

    def create_index(self, user, contents = None):
        index_name = ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
        # Mock the request to check if the index name exists
        Stock.mock_search([], symbol=index_name)
        cmd = "create " + index_name
        if contents:
            cmd += " " + contents
        response = self.index_call(user, cmd)
        return index_name, response

    def display_index(self, user, index_name = ''):
        cmd = index_name
        return self.index_call(user, cmd)

    def index_add(self, user, contents, index_name=None):
        cmd = "add "
        if index_name:
            cmd += index_name + " "
        cmd += contents
        return self.index_call(user, cmd)

    def index_call(self, user, command):
        return self.client.post('/indexes/', {'user_id': user, 'user_name': user, 'text': command})
