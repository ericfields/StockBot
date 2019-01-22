from django.test import TestCase, Client
import string
import random

class PortfolioViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_create_portfolio(self):
        name, response = self.create_portfolio('bob', 'AAPL AMZN:2')
        self.assertContains(response, name)
        self.assertContains(response, 'AAPL: 1')
        self.assertContains(response, 'AMZN: 2')

    def test_display_portfolio(self):
        name, response = self.create_portfolio('bob', 'AAPL AMZN:2')
        self.assertEquals(200, response.status_code)
        response = self.display_portfolio('bob', name)
        self.assertContains(response, name)
        self.assertContains(response, 'AAPL: 1')
        self.assertContains(response, 'AMZN: 2')

    def test_create_multiple_portfolios(self):
        name, response = self.create_portfolio('bob', 'AAPL:3 AMZN:4')
        self.assertContains(response, name)
        self.assertContains(response, 'AAPL: 3')
        self.assertContains(response, 'AMZN: 4')
        name, response = self.create_portfolio('bob', 'AAPL:5 AMZN:6')
        self.assertContains(response, name)
        self.assertContains(response, 'AAPL: 5')
        self.assertContains(response, 'AMZN: 6')

    def test_list_multiple_portfolios(self):
        name1, _ = self.create_portfolio('bob', 'AAPL:1 AMZN:2')
        name2, _ = self.create_portfolio('bob', 'AAPL:3 AMZN:4')

        response = self.display_portfolio('bob')
        self.assertContains(response, 'You have multiple portfolios.')
        self.assertContains(response, name1)
        self.assertContains(response, name2)

        response = self.display_portfolio('bob', name1)
        self.assertContains(response, name1)
        response = self.display_portfolio('bob', name2)
        self.assertContains(response, name2)

    def test_portfolio_ownership(self):
        bobs, _ = self.create_portfolio('bob', 'AAPL:1 AMZN:2')
        alices, _ = self.create_portfolio('alice', 'AAPL:3 AMZN:4')

        response = self.display_portfolio('bob', bobs)
        self.assertContains(response, bobs)
        self.assertNotContains(response, alices)
        response = self.display_portfolio('alice', alices)
        self.assertContains(response, alices)
        self.assertNotContains(response, bobs)

        response = self.display_portfolio('bob', alices)
        self.assertContains(response, 'You do not own this portfolio')
        response = self.display_portfolio('alice', bobs)
        self.assertContains(response, 'You do not own this portfolio')

    def test_portfolio_add(self):
        name, response = self.create_portfolio('bob')
        self.assertContains(response, name)

        response = self.portfolio_add('bob', 'AAPL AMZN:2')
        self.assertContains(response, 'AAPL')
        self.assertContains(response, 'AMZN')

        response = self.portfolio_add('bob', 'MSFT', name)
        self.assertContains(response, name)
        self.assertContains(response, 'MSFT')
        self.assertContains(response, 'AAPL')
        self.assertContains(response, 'AMZN')



    def create_portfolio(self, user, contents = None):
        portfolio_name = ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
        cmd = "create " + portfolio_name
        if contents:
            cmd += " " + contents
        response = self.portfolio_call(user, cmd)
        return portfolio_name, response

    def display_portfolio(self, user, portfolio_name = ''):
        cmd = portfolio_name
        return self.portfolio_call(user, cmd)

    def portfolio_add(self, user, contents, portfolio_name=None):
        cmd = "add "
        if portfolio_name:
            cmd += portfolio_name + " "
        cmd += contents
        return self.portfolio_call(user, cmd)

    def portfolio_call(self, user, command):
        return self.client.post('/portfolios/', {'user_id': user, 'user_name': user, 'text': command})
