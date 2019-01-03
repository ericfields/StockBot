from django.test import TestCase, Client

class PortfolioTestCase(TestCase):
    def setUp(self):
        pass

    def test_portfolio_create_succeeds(self):
        client = Client()
        response = client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob', 'text': 'create BOB AAPL AMZN'})
        self.assertEqual(200, response.status_code)
