from pathlib import Path
from django.test import TestCase
from .authenticator import TokenAuthenticator, load_authenticator_instance, _load_authenticator
from credentials import robinhood_credentials
from .oauth_token import OAuthToken
from unittest import SkipTest
import tempfile
import requests

class AuthTestCase(TestCase):
    credentials_path = Path(Path(__file__).parent.parent.parent, 'credentials')
    device_id_file = Path(credentials_path, '.device_id')
    oauth_token_file = Path(credentials_path, '.oauth_token')
    
    @classmethod
    def setUpClass(cls):
        cls.__check_if_file_present_with_content(cls.device_id_file)
        cls.__check_if_file_present_with_content(cls.oauth_token_file)
        super().setUpClass()

    @classmethod
    def __check_if_file_present_with_content(cls, file: Path):
        if not file.exists():
            raise SkipTest(f"Required file is not present: {file}")
        if not file.read_text().strip():
            raise SkipTest(f"Required file has no content: {file}")

    def test_authenticate_with_values(self):
        oauth_token = self.authenticate_and_refresh(self.device_id_file.read_text().strip(), self.oauth_token_file.read_text().strip())
        self.assertTrue(oauth_token) # True if not None or empty
        
        # The old token has been invalidated due to the refresh.
        # We must write the new token to the token file so other tests can use it.
        oauth_token.write_to_file(self.oauth_token_file)

    def test_authenticate_with_files(self):
        oauth_token = self.authenticate_and_refresh(self.device_id_file, self.oauth_token_file)
        self.assertTrue(oauth_token) # True if not None or empty

        # Repeat the authentication call to verify that the token file has been updated with the new token
        oauth_token = self.authenticate_and_refresh(self.device_id_file, self.oauth_token_file)
        self.assertTrue(oauth_token) # True if not None or empty
    
    def test_load_authenticator_instance(self):
        authenticator = load_authenticator_instance()
        self.assertIsInstance(authenticator, TokenAuthenticator)

        # Verify that we do not initialize the authenticator more than once
        self.assertIs(authenticator, load_authenticator_instance())

    def test_load_authenticator(self):
        authenticator = load_authenticator_instance()
        self.assertIsNotNone(authenticator)

        new_authenticator = _load_authenticator()
        self.assertIsNotNone(authenticator)

        # Verify that the authenticator is reinitialized
        self.assertIsNot(authenticator, new_authenticator)

    def test_load_authenticator_missing_credentials(self):
        device_id = robinhood_credentials.device_id
        try:
            # Check with a file that doesn't exist
            robinhood_credentials.device_id = Path('.nonexistent')
            self.assertIsNone(_load_authenticator())

            # Check with an empty credential
            with tempfile.NamedTemporaryFile(mode='w') as temp_device_id:
                robinhood_credentials.device_id = Path(temp_device_id.name)
                self.assertIsNone(_load_authenticator())
        finally:
            robinhood_credentials.device_id = device_id


    def authenticate_and_refresh(self, device_id: str | Path, token: str | Path) -> OAuthToken:
        authenticator = TokenAuthenticator(device_id, token, refresh_on_initial_load=False)
        self.assertIsNotNone(authenticator.auth_provider())

        test_url = 'https://api.robinhood.com/accounts/?default_to_all_accounts=true&include_managed=true&include_multiple_individual=false&is_default=false'

        # Test request using the authentication details from the authenticator
        response = requests.get(test_url, auth=authenticator.auth_provider())
        self.assertEqual(200, response.status_code, f"Initial auth failed\n{TokenAuthenticator.response_details(response)}")

        # Test token refresh
        self.assertTrue(authenticator.refresh_token())

        # Now test request once more with latest auth details
        response = requests.get(test_url, auth=authenticator.auth_provider())
        self.assertEqual(200, response.status_code, f"Initial auth failed\n{TokenAuthenticator.response_details(response)}")

        return authenticator.oauth_token