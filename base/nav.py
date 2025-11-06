
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .utils.nav import NavItem


navbar = [
    NavItem(title=_('Order'), paths='ledger:main'),
    NavItem(title=_('Accounts'), paths='ledger:account_list', path_prefixes='ledger:account_'),
    NavItem(title=_("Transactions"), paths='ledger:transaction_list'),
    NavItem(title=_('Stock'), paths='ledger:stock'),
    NavItem(title=_('Wiki'), paths='wiki:main', path_prefixes='wiki:'),
]

if settings.DEBUG:
    navbar += [
        NavItem(title="Test", paths=['ledger:test_detail'], permissions=('view_transactions',)),
        NavItem(title="Recipes", paths=['blackbook:recipes', 'blackbook:recipe'])
	]
