import json
from datetime import datetime, timedelta
from pathlib import Path

class OAuthToken():
    access_token: str
    expires_in: int
    refresh_token: str
    scope: str

    # The Robinhood token does not natively provide us with these fields.
    # We specify them at token refresh time.
    created_at: datetime = None
    expiration: datetime

    token_json: dict

    def __init__(self, oauth_token_str: str, created_at: datetime=None):
        try:
            self.token_json = json.loads(oauth_token_str)
        except Exception as e:
            raise ValueError("Could not parse OAuth token as JSON", e)

        try:
            self.access_token = self.load_key('access_token', required=True)
            self.expires_in = self.load_key('expires_in', required=True)
            self.scope = self.load_key('scope', required=True)
            self.refresh_token = self.load_key('refresh_token')

            created_at_timestamp = self.load_key('created_at')
        except Exception as e:
            raise ValueError("Could not parse OAuth token from JSON", e)
        
        if created_at_timestamp:
            self.created_at = datetime.fromtimestamp(created_at_timestamp)
        elif created_at:
            self.created_at = created_at

        if self.created_at:
            self.expiration = self.created_at + timedelta(seconds=self.expires_in)
        else:
            self.expiration = datetime.now()
        
    def to_json(self) -> str:
        if self.created_at:
            self.token_json['created_at'] = round(self.created_at.timestamp())
            
        return json.dumps(self.token_json, indent=4)
    
    def write_to_file(self, file: Path | str):
        if isinstance(file, str):
            file = Path(file)
        file.write_text(self.to_json())
    
    def seconds_until_expiry(self) -> int:
        return round((self.expiration - datetime.now()).total_seconds())
        
    def load_key(self, key: str, required: bool = False):
        if key in self.token_json:
            return self.token_json[key]
        elif required:
            raise Exception(f"Required key not in token JSON: {key}")
        return None