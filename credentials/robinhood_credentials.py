from pathlib import Path

__credentials_path = Path(__file__).parent

# UUID value which is unique between Robinhood clients.
# Found in the cookie named 'device_id' in a robinhood.com web session.
# For a given user, the value should remain unchanged for that particular web browser,
# even between web sessions.
device_id = Path(__credentials_path, '.device_id')

# OAuth token from a Robinhood web session. Can be obtained from a robinhood.com web session,
# from Local Storage under the key 'web:auth_state'
oauth_token = Path(__credentials_path, '.oauth_token')

# This value identifies the type of application calling Robinhood.
# This value is the same for all Robinhood web sessions; and is not expected to change often, if at all.
# In other words, don't modify this value unless you find that you need to.
# The value is buried within Robinhood's minified JavaScript, it can only neatly be derived
# by inspecting an OAuth2 token request on robinhood.com at login time (api.robinhood.com/oauth2/token)
# and looking for the value of 'client_id' in the JSON request body.
client_id = 'c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS'
