from django.test import TestCase, Client
from helpers.test_helpers import *

class NewsTestCase(TestCase):

    def setUp(self):
        self.client = Client()

    def test_news(self):
        stock = mock_stock('FB')
        mock_news(stock)
        response = self.client.get('/news/FB')
        self.assertEqual(response.status_code, 200)

    def test_mattermost_news(self):
        stock = mock_stock('FB')
        mock_news(stock)
        response = self.client.post('/news/', {'text': 'FB'})
        self.assertTrue('text' in response.json())
