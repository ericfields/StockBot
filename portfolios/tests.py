from django.test import TestCase, Client

class PortfolioViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_create_portfolio(self):
        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob', 'text': 'create BOBA AAPL AMZN:2'})
        self.assertContains(response, 'BOBA')
        self.assertContains(response, 'AAPL: 1')
        self.assertContains(response, 'AMZN: 2')

    def test_display_portfolio(self):
        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob', 'text': 'create BOBB AAPL AMZN:2'})
        self.assertEquals(200, response.status_code)
        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob'})
        self.assertContains(response, 'BOBB')
        self.assertContains(response, 'AAPL: 1')
        self.assertContains(response, 'AMZN: 2')

    def test_create_multiple_portfolios(self):
        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob', 'text': 'create BOBC AAPL:3 AMZN:4'})
        self.assertContains(response, 'BOBC')
        self.assertContains(response, 'AAPL: 3')
        self.assertContains(response, 'AMZN: 4')
        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob', 'text': 'create BOBD AAPL:5 AMZN:6'})
        self.assertContains(response, 'AAPL: 5')
        self.assertContains(response, 'AMZN: 6')

    def test_list_multiple_portfolios(self):
        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob', 'text': 'create BOBE AAPL:1 AMZN:2'})
        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob', 'text': 'create BOBF AAPL:3 AMZN:4'})

        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob'})
        self.assertContains(response, 'You have multiple portfolios.')
        self.assertContains(response, 'BOBE')
        self.assertContains(response, 'BOBF')

        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob', 'text': 'BOBF'})
        self.assertContains(response, 'BOBF')
        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob', 'text': 'BOBE'})
        self.assertContains(response, 'BOBE')

    def test_portfolio_ownership(self):
        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob', 'text': 'create BOBG AAPL:1 AMZN:2'})
        response = self.client.post('/portfolios/', {'user_id': 'alice', 'user_name': 'alice', 'text': 'create ALICEA AAPL:3 AMZN:4'})

        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob'})
        self.assertContains(response, 'BOBG')
        response = self.client.post('/portfolios/', {'user_id': 'alice', 'user_name': 'alice'})
        self.assertContains(response, 'ALICEA')
        self.assertNotContains(response, 'BOBG')

        response = self.client.post('/portfolios/', {'user_id': 'bob', 'user_name': 'bob', 'text': 'ALICEA'})
        self.assertContains(response, 'You do not own this portfolio')
        response = self.client.post('/portfolios/', {'user_id': 'alice', 'user_name': 'alice', 'text': 'BOBG'})
        self.assertContains(response, 'You do not own this portfolio')
