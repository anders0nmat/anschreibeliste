from utils.settings import AppSettings

from datetime import timedelta

TRANSACTION_TIMEOUT = timedelta(seconds=10)
SUBMIT_OVERLAY = timedelta(seconds=1.5)

BANKING = None

REVERT_THRESHOLD = timedelta(hours=6)
TIMEJUMP_THRESHOLD = timedelta(hours=12)

TRANSACTION_HISTORY_MIN_ENTRIES = 10
TRANSACTION_HISTORY_OLD_THRESHOLD = timedelta(hours=12)

settings = AppSettings('LEDGER', globals())
