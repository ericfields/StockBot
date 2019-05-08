from django.test import TestCase
from robinhood.models import *

class RobinhoodTestCase(TestCase):
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
