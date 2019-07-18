# StockBot

This is an integration for Mattermost which displays up-to-date charts of a stock's performance. It can display charts for options as well.

This bot also supports the ability for users to create and maintain a "index" of
stocks and options. Users can then display charts with the overall performance of these indexes, just as they would for a stock.

This service utilizes the (unofficial) [Robinhood API](https://github.com/sanko/Robinhood) to retrieve stock quote information and history.

## Installation

### Initial setup

First ensure that you have Python3 and pip installed.

Once installed, you can install this package's dependencies with pip as follows:

```
pip3 install -r requirements.txt
```

### Robinhood Authentication

In order to retrieve stock quote data, you'll need to set the following values in the `credentials.py` file:
`robinhood_username`: Your Robinhood account username
`robinhood_password`: Your Robinhood account password
`robinhood_device_token`: A UUID value which is unique between Robinhood users. This can be obtained by logging into Robinhood via browser or app, and doing a Ctrl+F for "clientId:".

Note that StockBot only uses these credentials to retrieve stock quote data, and does not retrieve or interact with any user-specific information, such as the details of stocks in a user's Robinhood index.

### Running StockBot

Once setup is complete, you can start the app by running the Django server.

```
python3 manage.py runserver
```

You can specify a specific port/interface to run the server on. To make the application externally accessible on port 8080 for example:

```
sudo python3 manage.py runserver 0.0.0.0:8080
```

## Features

### Stock Charts

You can create Mattermost outgoing hooks or slash commands for calling the bot. To call the stock chart endpoint for example, you could create a slash command called `/quote` that points to `http://[server-name]:[port]/stocks/quotes`.

You can then retrieve a chart as follows:

`/quote AAPL`

If you provide a Robinhood username/password, you can also quote options! For example, to quote an AAPL $250 call expiring January 1, 2019:

`/quote AAPL250C@1-1-2019`

See [QUOTES.md](documentation/QUOTES.md) for more info and options for on quoting stocks and options.

### Indexes

You can create a custom index of stocks and options, and quote its overall value! For example:

```
/index create MYSTUFF AAPL:2, AMZN:1
/quote MYSTUFF
```

Indexes require a database to be configured. See [INDEX.md](documentation/INDEXES.md) for more info on enabling Index support, as well as instructions on tracking and quoting indexes.

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
