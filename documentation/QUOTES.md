# Quotes

StockBot allows a user to retrieve price charts for both stocks and options.

## Mattermost Commands

The Mattermost endpoint for retrieving quotes is `/stocks/quotes`.

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

The result is a graph which is a sum of all these stocks' performance. StockBot will allow you to quote up to ten stocks at once.

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

### Quoting Portfolios

You can quote users' portfolios just as you would a stock.

`/quote FOLIO`

When you quote multiple user portfolios, a different line will be plotted for each portfolio, making it easy for users to compare their performance.

`/quote MYSTUFF,YOURSTUFF`

Note that only user portfolios will be displayed on separate lines. Other queried assets, i.e. stocks/options, will be lumped into a single aggregate line.

You can quote up to ten stocks/options/portfolios at once.

`/quote MYSTUFF,YOURSTUFF,AMZN,AAPL`

## GET endpoints:

For testing or other purposes, there is also a standard GET endpoint configured for viewing charts. You can visit the endpoint /stocks/quotes/[stock_ticker] to retrieve a PNG image of the graph. For example, to get a PNG of the latest AAPL graph for the day: http://127.0.0.1:8000/stocks/quotes/AAPL

Some examples:

* `/stocks/quotes/AAPL`: Day chart of AAPL
* `/stocks/quotes/AAPL/1w`: Chart of AAPL for the past week
* `/stocks/quotes/MU50.5C@12-21`: Chart of MU 50.5 call expiring 12/21 (current year)
* `/stocks/quotes/MU50.5P/1m`: Chart of MU 50.5 put, expiring at the end of the week, with data for the past month
