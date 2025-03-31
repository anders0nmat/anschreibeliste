from django.conf import settings
from django.urls import path, include

from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="main"),
    path("accounts/", views.AccountList.as_view(), name="account_list"),
    path("accounts/new/", views.AccountCreate.as_view(), name="account_create"),
    path("accounts/<pk>/", views.AccountDetail.as_view(), name="account_detail"),
    
	path("transaction/", include([
		path("deposit/", views.custom_transaction, {'action': 'deposit'}),
		path("withdraw/", views.custom_transaction, {'action': 'withdraw'}),
		path("order/", views.product_transaction),
		path("revert/", views.revert_transaction, name="transaction_revert"),
	])),
    
	path("api/transaction/", include([
		path("deposit/", views.custom_transaction_ajax, {'action': 'deposit'}, name='api_deposit'),
		path("withdraw/", views.custom_transaction_ajax, {'action': 'withdraw'}, name="api_withdraw"),
		path("order/", views.product_transaction_ajax, name='api_order'),
		path("revert/", views.revert_transaction_ajax, name='api_revert'),
		path("events/", views.transaction_events, name="api_events"),
	])),
]

if settings.DEBUG:
    urlpatterns += [
		path("test/", views.test, name='test_detail'),
		path("test/events/", views.event),
		path("test/send_event/", views.send)
	]
