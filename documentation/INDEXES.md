# Indexes

StockBot allows Mattermost users to group stocks and options into indexes. Users can then quote this index to see how it's performing overall. Quoting an index only shows the percentage gain/loss, and doesn't display the actual dollar value of the assets within.

The endpoint for creating and managing indexes is `/stocks/index`. For these examples, we'll assume that we have a Mattermost slash command named `/index`.

(note: It's recommended to use slash commands for these activities, if you want to hide the actual number shares/contracts of the assets within.)

## Using Indexes

### Creating an index:

Every index needs a symbol of its own, so that you and other users can quote it. To create your own index named "MYSTUFF":

`/index create MYSTUFF`

Users can create multiple indexes. Once created, no other user can create an index with that symbol, unless the owner decides to delete or rename theirs.

You can define your index with any stocks or options you'd like, in any number. For example, to create an index named MYSTUFF that holds:
* One share of AMZN
* 2 shares of AAPL
* 3 AMD $50 calls expiring December 21

...you would enter the following:

`/index create MYSTUFF AMZN AAPL:2, AMD50C12-21:3`

Note that a stock/option identifier with no number after it represents one share/contract of that asset.

You can recreate the index in this same way at any time. Note that recreating the index deletes any of the old assets you had, and remakes them from scratch!

To rename your index:

`/index rename MYSTUFF MYNEWSTUFF`

or if you only have one index:

`/index rename MYNEWSTUFF`

Any user can see the contents of any index as follows:

`/index MYSTUFF`

would return

```
MYSTUFF:
  AMZN: 1 50%
  AAPL: 2 20%
  AMD50.0C@12-21-2018: 30%
```

When a user requests the contents of an index they themselves have created, they will see the actual cash value of the assets inside.

```
MYSTUFF ($3000):
  AMZN: 1 ($2000, 50%)
  AAPL: 2 ($400, 20%)
  AMD50.0C@12-21-2020: ($600, 30%)
```

If you have only created a single index, you can simply view the contents as follows:

`/index`

Keep in mind, other users using the `/index` command to view your index will see a list of stocks/options you have, along with the percentage of the index that each one makes up. However, those users will not see the total cash value of the shares/contracts in the index.

### Tracking your assets:

If you want to add an asset to your index:

`/index add AAPL:2`

Similarly, to remove assets:

`/index remove AAPL:2`

If you do not specify the number of assets to remove, all shares/contracts for that asset will be removed.

`/index remove AAPL` (removes both AAPL shares from the index)

You can specify multiple assets to add/remove:

`/index add AAPL:2 AMZN`
`/index remove AAPL:1 AMD50C12/21`

Finally, to delete your index and all its assets:

`/index delete`

### Quoting indexes

You can quote an index and view a graph for it just as you can a stock or an option. Any user can quote any index.

Note that the actual cash value of the assets inside the index are hidden in these graphs. Only its percentage increase/decrease is shown.

The quotes endpoint is `/stocks/quotes`. For this example, we will assume that we have a Mattermost slash command pointing to this endpoint named `/quote`.

To quote an index a user has created with the name "MYSTUFF":

`/quote MYSTUFF`

This will return a chart that displays the performance of the index for the day.

You can also request a longer date range:

`/quote MYSTUFF 2weeks`

When you quote multiple user indexes, a different line will be plotted for each index, making it easy for users to compare their performance. Note that only the percentage change of each index will be displayed; no actual dollar amounts are revealed.

`/quote MYSTUFF,YOURSTUFF`

You can quote up to ten indexes at once.
