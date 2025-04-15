from django.utils.translation import gettext_lazy as _
from typing import TypedDict

class BankingInfo(TypedDict):
    name: str
    iban: str
    invoice_text: str


TRANSACTION_TIMEOUT: int = 10_000
"""
How long until an unfinished transaction will be discarded.

Unit: ms (milliseconds)
Default value: 10_000
"""

SUBMIT_OVERLAY: int = 1_500
"""
How long the confirmation/error overlay is shown after submitting a transaction.

Unit: ms (milliseconds)
Default value: 1_500
"""

BANKING_INFORMATION: BankingInfo | None = None
"""
This information is displayed for permanent members to transfer money to.

If set to `None`, this feature is disabled.
Otherwise, set to a dict conforming to `BankingInfo`

Field `invoice_text` wil be formatted before use with `.format(name=account.name)` before use,
so it may contain format pattern `'{name}'`, e.g. 
```py
'invoice_text': 'Deposit of money from {name}'
```

Default value: None
"""
