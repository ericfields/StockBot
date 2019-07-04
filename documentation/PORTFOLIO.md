# Portfolios

StockBot allows Mattermost users to create and quote their own portfolios! (without needing a Robinhood account). Quoting a portfolio only shows the percentage gain/loss, and doesn't display the actual value or content of a user's assets in any way.

**Note**: Creating a portfolio doesn't mean you're actually buying/selling stocks...it's just a neat way to see how you and others are performing!

The endpoint for creating and managing portfolios is `/stocks/portfolio`. For these examples, we'll assume that we have a Mattermost slash command named `/portfolio`. Note that it's important to use a slash command for these activities, if you want to hide the actual contents of your portfolio!

## Using Portfolios

### Creating a portfolio:

Every portfolio needs a symbol of its own, so that you and other users can quote it. To create your own portfolio named "MYSTUFF":

`/portfolio create MYSTUFF`

Each user can create exactly one portfolio, and that portfolio is tied to that user's Mattermost account. Once created, no other user can make a portfolio with that symbol, unless the owner decides to delete or rename theirs.

You can initialize your profile with any cash, stocks, and options you'd like. For example, to create a portfolio named MYSTUFF that holds:
* $1000 cash
* One share of AMZN
* 2 shares of AAPL
* 3 AMD $50 calls expiring December 21

...you would enter the following:

`/portfolio create MYSTUFF $1000 AMZN AAPL:2, AMD50C12-21:3`

Note that a stock/option identifier with no number after it represents one of that asset.

You can recreate the portfolio in this same way at any time. Note that recreating the portfolio deletes any of the old assets you had, and remakes them from scratch!

Each user can only have one portfolio. To rename your portfolio:

`/portfolio rename MYNEWSTUFF`

You can see the contents of your own portfolio by simply running the command with no arguments:

`/portfolio`

...returns...

```
MYSTUFF:
  Cash: $1000
  AMZN: 1
  AAPL: 2
  AMD50.0C@12-21-2018: 3
```

A user can only see the contents of their own portfolio, and only that user will see the results of these commands.

### Tracking your assets:

If you want to "buy" or "sell" one or more assets for your portfolio:

`/portfolio buy AAPL:2`

Using the `buy` command deducts from the cash amount you have defined for the portfolio. If you don't have enough cash, the `buy` command will display an error.

Similarly, to mark assets as sold:

`/portfolio sell AAPL:2`

You can specify multiple assets to buy/sell:

`/portfolio buy AAPL:2 AMZN`

This will remove the number of assets you specify and add the value of the asset to your portfolio's cash value.

If you simply want to add assets to your portfolio, increasing its overall value (and not modifying your cash value):

`/portfolio add AAPL:2`

You can add cash to your portfolio in the same way:

`/portfolio add $500`

To remove assets from your portfolio (subtracting from its overall value):

`/portfolio remove AAPL:2`

or

`/portfolio remove $500`

Finally, to delete your portfolio and all its assets:

`/portfolio delete`

### Quoting portfolios

You can quote a portfolio just as you can a stock or an option. Any user can quote a portfolio!

Note that the actual numeric values are removed so that no one knows the actual value of the portfolio...only it's percentage increase/decrease.

The quotes endpoint is `/stocks/quotes`. For this example, we will assume that we have a Mattermost slash command pointing to this endpoint named `/quote`.

To quote a portfolio a user has created with the name "MYSTUFF":

`/quote MYSTUFF`

This will return a chart that displays the performance of the portfolio for the day.

You can also request a longer date range:

`/quote MYSTUFF 2weeks`

When you quote multiple user portfolios, a different line will be plotted for each portfolio, making it easy for users to compare their performance. Note that only the percentage change of each portfolio will be displayed; no actual dollar amounts are revealed.

`/quote MYSTUFF,YOURSTUFF`

You can quote up to ten portfolios at once.

### Allowing other users to see your portfolio contents

By default, the actual contents of your portfolio are private, and only you can see them. You can choose to make your portfolio visible to others, with varying levels of detail, as follows:

```
/portfolio visibility private|listings|ratios|shares|public
```

For example, to change the visibility of your portfolio to "listings":
```
/portfolio visibility listings
```

...or if you have multiple portfolios, you can specify which one to modify:

```
/portfolio visibility MYSTUFF listings
```

Other users can now view the contents of your portfolio as follows (with limited information, depending on your visibility level):
```
/portfolio MYSTUFF
```
#### Visibility levels

For our examples, let's say we have a portfolio MYSTUFF that contains the following:
```
MYSTUFF ($1000.00)
  Cash: $500.00
  AAPL: 1 ($200.00)
  MSFT: 2 ($300.00)
```

The various visibility levels are as follows:
* `private` (default) - No other users can see the contents of your portfolio.
* `listings` - Users can see a list of the stocks/options you have in your portfolio, but they cannot see the number of shares/contracts you are holding for each. They cannot see the total value of your portfolio or its cash value either. For example, if another user quoted MYSTUFF they would see the following:
```
MYSTUFF
  AAPL
  MSFT
```
* `ratios` - Other users will see the proportion of your portfolio's total value which each set of stocks/options you have makes up. For example:
```
MYSTUFF
  AAPL: 20%
  MSFT: 30%
```
* `shares` - Other users will see the actual number of shares of each stock/option you have in your portfolio. For example:
```
MYSTUFF
  AAPL: 1 ($200.00)
  MSFT: 2 ($300.00)
```
* `public` - This makes the full details of your portfolio public. Other users will be able to see all of the information for your portfolio, i.e.:
```
MYSTUFF ($1000.00)
  Cash: $500.00
  AAPL: 1 ($200.00)
  MSFT: 2 ($300.00)
```
