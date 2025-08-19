
from utils.settings import AppSettings
from datetime import timedelta


COOKIE_KEY = 'autologin_user'

# Max age of autologin cookie.
# The cookie will be refreshed every time the user sends a request
# Therefore the cookie only expires if the user
# doesn't interact with the server for `COOKIE_MAX_AGE`
COOKIE_MAX_AGE = timedelta(weeks=12)


settings = AppSettings('AUTOLOGIN', globals())
