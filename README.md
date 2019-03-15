# StockBot

This is an integration for Mattermost which displays up-to-date charts of a stock's performance. It can display charts for options as well.

Users can also create their own custom portfolios and track their performance.

This service utilizes the (unofficial) [Robinhood API](https://github.com/sanko/Robinhood) to retrieve stock quote information and history.

## Installation

First ensure that you have Python3 and pip installed.

Once installed, you can install this package's dependencies with pip as follows:

```
pip3 install -r requirements.txt
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

### Robinhood Authentication

In order to retrieve stock quote data, you'll need to specify a valid Robinhood username and password in the `config.py` file.

## Features

### Stock Charts

You can create Mattermost outgoing hooks or slash commands for calling the bot. To call the stock chart endpoint for example, you could create a slash command called `/quote` that points to `http://[server-name]:[port]/stocks/quotes`.

You can then retrieve a chart as follows:

`/quote AAPL`

If you provide a Robinhood username/password, you can also quote options! For example, to quote an AAPL $250 call expiring January 1, 2019:

`/quote AAPL250C@1-1-2019`

See [QUOTES.md](QUOTES.md) for more info and options for on quoting stocks and options.

### Portfolios

You can create a custom stock portfolio (just for tracking, not actual buying and selling) and quote its overall value! For example:

```
/portfolio create MYSTUFF AAPL:2, AMZN:1
/quote MYSTUFF
```

See [PORTFOLIO.md](PORTFOLIO.md) for more info on tracking and quoting portfolios.

### News

StockBot can show you the latest news about a stock, using the `/news` endpoint.

To display an excerpt from the latest, most viewed news article regarding FB:

```
/news FB
```

Not enough info? If you wanted to see the three most relevant news item for FB:

```
/news FB 3
```

You can request up to ten news items at once for a stock.
