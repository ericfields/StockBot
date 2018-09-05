This is an integration for Mattermost which retrieves a graph of the past day's stock activity.

### API Keys

This service utilizes two APIs to retrieve stock information:
* The [Alpha Vantage API](https://www.alphavantage.co/documentation/), which provides stock price data
* The [OpenFigi](https://openfigi.com/api) API, which provides metadata about stocks/securities such as the company name

Both of these APIs are free to use; however, it is advisable to have an API key for each of them. Otherwise, your requests will be throttled significantly (particularly the AlphaVantage API, which naturally needs to be called more frequently).

Although both API keys are free to obtain, the OpenFigi API requires an institutional email (e.g. a company email domain such as google.com). You can optionally go without using an API key for OpenFigi, as this bot caches stock information as it arrives and should not need to call the OpenFigi API very frequently.

It should also be noted that even with an API key, the free Alpha Vantage API uses significant throttling, and a few calls within a 5 second period are generally enough to be throttled and thus forced to wait about 30 seconds before the next call succeeds. This bot will delay returning your calls if they are throttled.

Alpha Vantage API key: https://www.alphavantage.co/support/

OpenFigi API key: https://openfigi.com/api

### Installation

First ensure that you have Python3 and pip installed.

Once installed, you can install this package's dependencies with pip as follows:

```
pip install -r requirements.txt
```

You can then run the app by starting the Django server.

```
python3 manage.py runserver
```

To run the server so that is externally accessible (not recommended if used in production) on port 80, you can run it as follows:
```
sudo python3 manage.py runserver 0.0.0.0:80
```

### Calling the Bot

You can create a Mattermost slash command for calling the bot, then invoke it by providing the stock ticker as its argument.
* Create a Mattermost integration as an outgoing webhook or slash command, and provide your server endpoint with the path `/stocks/graph` as the request URL. For example: `http://127.0.0.1:8000/stocks/graph`.
* Get a stock graph by invoking the command and with the stock ticker as its argument. For example, if you created a slash command called `/quote`, you would use: `/quote AAPL`:

This will return a graph with the requested stock chart for AAPL for the day.

For testing or other purposes, there is also a standard GET endpoint configured for viewing charts. You can visit the endpoint /stocks/graph/[stock_ticker] to retrieve a PNG image of the graph. For example, to get a PNG of the latest AAPL graph for the day:

```
http://127.0.0.1:80/stocks/graph/AAPL
```
