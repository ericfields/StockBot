import requests
import config
import json

BASE_URL = 'https://api.openfigi.com/v1/mapping'
API_KEY = config.openfigi_api_key

def get_stock_company(symbol):
    headers = {
        'Content-Type': 'application/json',
    }
    if API_KEY:
        headers['X-OPENFIGI-APIKEY'] = API_KEY
        
    payload = [{
        "idType": "TICKER",
        "idValue": symbol,
        "exchCode": "US"
    }]
    r = requests.post(BASE_URL, data=json.dumps(payload), headers=headers)

    if 'data' in r.json()[0]:
        return r.json()[0]['data'][0]['name']
    else:
        return None
