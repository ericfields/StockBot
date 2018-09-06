This is an integration for Mattermost which retrieves a graph of the past day's stock activity.

### API Keys

This service utilizes the (unofficial) [Robinhood API](https://github.com/sanko/Robinhood) to retrieve stock quote information and history.

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
