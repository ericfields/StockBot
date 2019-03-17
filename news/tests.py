from django.test import TestCase, Client

class NewsTestCase(TestCase):

    def setUp(self):
        self.client = Client()

    def test_news(self):
        response = self.client.get('/news/FB')
        self.assertEqual(response.status_code, 200)

    def test_mattermost_news(self):
        response = self.client.post('/news/', {'text': 'FB'})
        self.assertTrue('text' in response.json())
