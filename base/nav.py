
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .utils.nav import NavItem


navbar = [
    NavItem(title=_('Order'), paths=['ledger:main']),
    NavItem(title=_('Accounts'), paths=[
        'ledger:account_list',
        'ledger:account_detail',
        'ledger:account_create']),
    NavItem(title=_("Transactions"), paths=['ledger:transaction_list']),
    NavItem(title=_('Stock'), paths=['ledger:stock']),
]

if settings.DEBUG:
    navbar += [
        NavItem(title="Test", paths=['ledger:test_detail'], permissions=('view_transactions',)),
	]
