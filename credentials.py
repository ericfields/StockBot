# Credentials required for quoting stocks and options

robinhood_username = None
robinhood_password = None

# UUID value which is unique between Robinhood clients.
# Must be obtained by logging in via browser or app and verifying via SMS/email code.
# You can find this by viewing the source on the Robinhood login page, and doing a Ctrl+F for "clientId:"
robinhood_device_token = None

# This value identifies the type of application calling Robinhood.
# It appears to be the same across all Robinhood Web clients, though it could be changed by Robinhood at some point in the future.
# You likely do not need to change this unless there is an issue.
# You can find the client ID by viewing the source on the Robinhood login page, and doing a Ctrl+F for "oauthClientId".
# view-source:https://robinhood.com/login
robinhood_oauth_client_id = 'c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS'
