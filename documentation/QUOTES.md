# Quotes

StockBot allows a user to retrieve price charts for both stocks and options.

## Raw Images

The simplest way to view a stock graph is by hitting the `/quotes/view` endpoint. For example, if you are running StockBot locally, you can visit the following URL in a browser:

`http://127.0.0.1:8000/quotes/view/AAPL`

You'll be given a PNG with a graph of AAPL for the current day. This endpoint is ideal for testing functionality, or simply providing graph images alone when needed.

Some examples:
* `/quotes/view/AAPL`: Day chart of AAPL
* `/quotes/view/AAPL/1w`: Day chart of AAPL for the past week
* `/quotes/view/GME50.5C@12-21`: Day chart of GME 50.5 call expiring 12/21 (current year)
* `/quotes/view/GME50.5P/1m`: Month chart of GME 50.5 put, expiring at the end of the week

## Mattermost Commands

The Mattermost endpoint for retrieving quotes is `/quotes`.

For the purpose of these examples, we will use a slash command called `/quote` to reference a command which calls the quotes endpoint.

### Quoting Stocks

To retrieve a day chart for AAPL:

`/quote AAPL`

You can retrieve charts for longer periods. To receive a chart for the past 10 days:

`/quote AAPL 10days`

Or you can abbreviate it:

`/quote AAPL 10d`

To see the entire history of AAPL (up to 5 years, the maximum Robinhood returns):

`/quote AAPL all`

You can retrieve time ranges with a granularity of days, weeks, months, or years:
`/quote AAPL week [n][day(s)/week(s)/month(s)/year(s)/all/d/w/m/y/all/a]`

The default is the day chart if no timespan is provided.

You can also retrieve a combined quote for multiple stocks at once, using comma-separated values (no spaces).

`/quote AAPL,GOOGL,AMZN [timespan]`

When quoting multiple stocks at once, each stock will be displayed on its own line.
For readability purposes, only the percentage change of each stock will be shown,
and the dollar values will be hidden.

StockBot will allow you to quote up to ten stocks at once.

### Quoting Options

StockBot supports quoting for stock options as well.

To retrieve a chart for an MU $50.5 call expiring at the end of the week (i.e. the earliest expiration possible):

`/quote MU50.5C`

Note that the value displayed in the chart will be that of a single option contract, i.e. the value of the option times 100.

To retrieve a chart for an AAPL $220 put option expiring November 16 (of the current year):

`/quote AAPL220P@11-16`

You can specify the year as well. You can also optionally leave out the '@' sign:

`/quote AAPL220P11-16-20`

You can request charts with longer timespans, just as you would for a stock chart.

`/quote AAPL220P 1w` (one week)

You can retrieve a chart for multiple options at once, just as you can with stocks. You can even get a chart containing stocks and options, all in the same command!

`/quote MU,AMD,AAPL220P,SNAP8P12-21`

Up to 10 stocks/options can be quoted at once.

### Quoting Indexes

You can quote users' indexes just as you would a stock.

`/quote FOLIO`

When quoting indexes, the actual dollar value of the index is hidden, and
only the percentage change of the index is displayed. This allows users
to maintain their index assets accurately without having to worry about other
users knowing how much money they actually have.

When you quote multiple user indexes, a different line will be plotted for each index, making it easy for users to compare their performance.

`/quote MYSTUFF,YOURSTUFF`

You can also quote indexes alongside stocks and options. You can quote up to ten stocks/options/indexes at once.

`/quote MYSTUFF,YOURSTUFF,AMZN,AAPL`