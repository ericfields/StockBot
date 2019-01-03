from django.test import TestCase, Client

class QuoteTestCase(TestCase):
    def setUp(self):
        pass

    def test_stock_quote_succeeds(self):
        client = Client()
        response = client.get('/quotes/view/AAPL')
        self.assertEqual(response.status_code, 200)
