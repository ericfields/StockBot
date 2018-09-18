This is an integration for Mattermost which retrieves a graph of the past day's stock activity.

### API Keys

This service utilizes the (unofficial) [Robinhood API](https://github.com/sanko/Robinhood) to retrieve stock quote information and history.

### Installation

First ensure that you have Python3 and pip installed.

Once installed, you can install this package's dependencies with pip as follows:

```
pip install -r requirements.txt
```

Next, run the following to execute the database migrations (you should only need to do this once):

```
python3 manage.py migrate
```

You can then start the app by running the Django server.

```
python3 manage.py runserver
```

To run the server so that is externally accessible (not recommended if used in production) on port 80, you can run it as follows:
```
sudo python3 manage.py runserver 0.0.0.0:80
```

### Features

You can create Mattermost outgoing hooks or slash commands for calling the bot. To call the stock graph endpoint for example, you could create a slash command that points to `http://[server-name]:[port]/stocks/graph`.

#### Stocks

Retrieve a stock chart for various stocks.

Endpoint: `/stocks/graph`.

To retrieve a day chart for AAPL:

`[command-name] AAPL`

You can retrieve charts for longer periods. To receive a chart for the past 10 days:

`[command-name] AAPL 10days`

Or you can abbreviate it:

`[command-name] AAPL 10d`

To see the entire history of AAPL (up to 5 years, the maximum Robinhood returns):

`[command-name] AAPL all`

You can retrieve time ranges with a granularity of days, weeks, months, or years:
`[command-name] AAPL week [n][day(s)/week(s)/month(s)/year(s)/all/d/w/m/y/all/a]`

The default is the day chart if no timespan is provided.


You can also retrieve a combined quote for multiple stocks at once.

`[command-name] AAPL,GOOGL,AMZN [timespan]`

The result is a graph which is a sum of all these stocks' performance.

#### Options

StockBot supports quoting for options as well. **Important**: The Robinhood endpoint for options history is authenticated. You will have to specify the username and password of a valid Robinhood account in the `config.py` file.

Endpoint: `/stocks/option/graph`

To retrieve a chart of an MU $50.5 call expiring November 16 (this year):

`/[command-name] MU 50.5C 11-16`

To retrieve a chart of a put for the same price, expiring January 18, 2019:

`/[command-name] MU 50.5P 1-18-2019`

# GET endpoints:

For testing or other purposes, there is also a standard GET endpoint configured for viewing charts. You can visit the endpoint /stocks/graph/[stock_ticker] to retrieve a PNG image of the graph. For example, to get a PNG of the latest AAPL graph for the day: http://127.0.0.1:8000/stocks/graph/AAPL

You can expand the date range you request a graph for:
* Stocks
  * `/stocks/graph/AAPL`: Day chart of AAPL
  * `/stocks/graph/AAPL/1W`: Chart of AAPL for the past week
* Options
* `/stocks/option/graph/MU/50.5C/12-21`: MU 50.5 call expiring 12/21 (current year)
* `/stocks/option/graph/MU/50.5P/1-18-2019`: MU 50.5 put expiring 1/21/2019
