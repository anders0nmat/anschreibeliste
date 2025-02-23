from django.urls import path

from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="main"),
    path("accounts/", views.AccountList.as_view(), name="account_list"),
    path("accounts/new", views.AccountCreate.as_view(), name="account_create"),
    path("accounts/<pk>/", views.AccountDetail.as_view(), name="account_detail"),
    path("test/", views.test),
    path("test/events/", views.event),
    path("test/send_event/", views.send),
    path("transaction/product/", views.product_transaction, name="product_transaction"),
    path("transaction/custom/", views.custom_transaction, name="custom_transaction"),
    path("transaction/revert/", views.revert_transaction, name="revert_transaction"),
	path("transaction/events/", views.transaction_event, name="transaction_event"),
]
