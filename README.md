# StockBot

This is an integration for Mattermost which displays up-to-date charts of a stock's performance. It can display charts for options as well.

This bot also supports the ability for users to create and maintain a "index" of
stocks and options. Users can then display charts with the overall performance of these indexes, just as they would for a stock.

This service utilizes the (unofficial) [Robinhood API](https://github.com/sanko/Robinhood) to retrieve stock quote information and history.

## Features

### Stock Charts

You can create Mattermost outgoing hooks or slash commands for calling the bot. To call the stock chart endpoint for example, you could create a slash command called `/quote` that points to `http://[server-name]:[port]/stocks/quotes`.

You can then retrieve a chart as follows:

`/quote AAPL`

If you provide Robinhood credentials, you can also quote options! For example, to quote an AAPL $250 call expiring January 1, 2019:

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

For example, to display an excerpt from the latest, most viewed news article regarding AAPL:

```
/news FB
```

Not the article you wanted? If you wanted to see the three most relevant news item for the stock:

```
/news AAPL 3
```

StockBot attempts to sort news articles by relevance. You can request up to ten news items at once for a stock.

## Installation

### Initial setup

First ensure that you have Python3 and pip installed.

Once installed, you can install this package's dependencies with pip as follows:

```
pip3 install -r requirements.txt
```

### Robinhood Authentication

In order to retrieve stock quote data, you'll need to set the following values in the `robinhood/credentials` directory:

* `device_id`: Identifier for the web client, unique between Robinhood clients. The value can be found in the cookie named 'device_id' in a robinhood.com web session. For a given user, the value should remain unchanged for that particular web browser, even between web sessions. You can specify this value in the file `credentials/.device_id` for convenience.

* `oauth_token`: OAuth access token from a Robinhood web session. You can obtain this value by from a robinhood.com web session, from Local Storage under the key 'web:auth_state'. You can specify this value in the file `credentials/.oauth_token` for convenience. StockBot will periodically refresh the token when it is near expiry; when the token is refreshed, the new token will be written to the `.oauth_token` file.

StockBot does not support username/password authentication, as Robinhood enforces two-factor authentication for these workflows; this would be painful for users to enact in the real world.

Note that StockBot only uses these credentials to retrieve stock quote data, and does not retrieve or interact with any user-specific information, nor does it perform any buying/selling operations. StockBot only uses Robinhood to retrieve price information about a stock.

### Running StockBot

Once setup is complete, the simplest way to run the app is by running the Django server as follows:

```
python3 manage.py runserver
```

You can specify a specific port/interface to run the server on. To make the application externally accessible on port 8080 for example:

```
sudo python3 manage.py runserver 0.0.0.0:8080
```

For tips on a more production-level setup, i.e. using StockBot with a web server, SSL, etc., see [SETUP_NOTES.md](documentation/SETUP_NOTES.md).
