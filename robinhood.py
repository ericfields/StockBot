import requests

ROBINHOOD_ENDPOINT = 'https://api.robinhood.com'

ENDPOINTS = {
    'quote': '/quotes',
    'historicals': '/quotes/historicals',
    'instrument': '/instruments',
    'fundamentals': '/fundamentals'
}

def endpoint(name):
    return ROBINHOOD_ENDPOINT + ENDPOINTS[name]

def retrieve(endpoint_name, resource = None, **params):
    request_url = endpoint(endpoint_name) + '/'
    if resource:
        request_url += "{}/".format(resource)
    if params:
        param_str = "&".join(["{}={}".format(key, params[key]) for key in params])
        request_url += '?' + param_str

    response = requests.get(request_url)
    if response.status_code != 200:
        return {}
        
    return response.json()

def historicals(symbol, span='day', interval='5minute'):
    return retrieve('historicals', symbol, span=span, interval=interval, bounds='trading')

def quote(symbol):
    return retrieve('quote', symbol)

def instrument(symbol):
    return retrieve('instrument', symbol=symbol)

def fundamentals(symbol):
    return retrieve('fundamentals', symbol)
