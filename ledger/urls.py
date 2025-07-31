from django.conf import settings
from django.urls import path, include

from . import views
from .models import Product

app_name = "ledger"
urlpatterns = [
    path("", views.IndexView.as_view(), name="main"),
    path("stock/", views.IndexView.as_view(product_category=Product.ProductCategory.STOCK), name="stock"),
    path("accounts/", views.AccountList.as_view(), name="account_list"),
    path("accounts/new/", views.AccountCreate.as_view(), name="account_create"),
    path("accounts/<pk>/", views.AccountDetail.as_view(), name="account_detail"),
    path("accounts/<pk>/revert/", views.revert_transaction, name="account_revert"),

    path("transactions/", views.TransactionList.as_view(), name="transaction_list"),
    path("transactions/csv/", views.TransactionList.as_view(output_format="csv")),
    path("transactions/xlsx/", views.TransactionList.as_view(output_format="xlsx")),
    path("transactions/results/", views.TransactionList.as_view(template_name="ledger/transaction_list_results.html")),
    
	path("transaction/", include([
		path("deposit/", views.custom_transaction, {'action': 'deposit'}, name="transaction_deposit"),
		path("withdraw/", views.custom_transaction, {'action': 'withdraw'}, name="transaction_withdraw"),
		path("order/", views.product_transaction),
		path("revert/", views.revert_transaction, name="transaction_revert"),
	])),
    
	path("api/transaction/", include(([
		path("deposit/", views.custom_transaction, {'action': 'deposit'}, name='deposit'),
		path("withdraw/", views.custom_transaction, {'action': 'withdraw'}, name="withdraw"),
		path("order/", views.product_transaction, name='order'),
		path("revert/", views.revert_transaction, name='revert'),
		path("events/", views.transaction_events, name="events"),
		path("ping/", views.transaction_ping, name="ping"),
	], "api"))),
]

if settings.DEBUG:
    urlpatterns += [
		path("test/", views.test, name='test_detail'),
        path("test/events/", views.test_event),
        path("test/send_event/", views.send_test_event),
	]
