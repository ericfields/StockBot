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

#### Stock Charts

You can create a Mattermost slash command for calling the bot, then invoke it by providing the stock ticker as its argument.
* Create a Mattermost integration as an outgoing webhook or slash command, and provide your server endpoint with the path `/stocks/graph` as the request URL. For example: http://127.0.0.1:8000/stocks/graph.
* Get a stock graph by invoking the command and with the stock ticker as its argument. For example, if you created a slash command called `/quote`, you would use: `/quote AAPL`


This will return a graph with the requested stock chart for AAPL for the day.

For testing or other purposes, there is also a standard GET endpoint configured for viewing charts. You can visit the endpoint /stocks/graph/[stock_ticker] to retrieve a PNG image of the graph. For example, to get a PNG of the latest AAPL graph for the day: http://127.0.0.1:8000/stocks/graph/AAPL

You can expand the date range you request a graph for:
* GET request URL examples:
  * Past week:
    * `/stocks/graph/AAPL/week`
    * `/stocks/graph/AAPL/w`
  * Past 10 days:
    * `/stocks/graph/AAPL/10days`
    * `/stocks/graph/AAPL/10d`
  * Past 2 years:
    * `/stocks/graph/AAPL/2year`
    * `/stocks/graph/AAPL/2y`
  * Full history (as far back as 5 years, max data Robinhood contains):
    * `/stocks/graph/AAPL/all`
    * `/stocks/graph/AAPL/a`
* Mattermost example commands (Command named /quote pointing to /stocks/graph):
  * `/[command-name] AAPL 1y`
  * `/[command-name] AAPL all`

#### Option Charts (authentication required)

You can also retrieve a chart for a stock option, at the endpoint `/stocks/option/graph`. Note however that the endpoint for retrieving Options history is authenticated, and thus you will have to provide credentials for a valid Robinhood account in your config.py file.

For example, to view an option for an MU $90 call expiring December 21 of that year:
* MU $50 call option expiring November 16 of current year
  * GET request: `/stocks/option/MU/50C/11-16/`
  * Mattermost: `/[command-name] MU 50C 11-16`
* MU $40 put option expiring January 18, 2019
  * GET request: `/stocks/option/graph/MU/40P/1-18-19`
  * Mattermost: `/[command-name] MU 40P 1-18-19`
