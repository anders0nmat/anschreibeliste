from django.urls import path
import django_eventstream

from . import views

urlpatterns = [
    path("", views.main, name="main"),
    path("accounts/", views.AccountList.as_view(), name="account_list"),
    path("accounts/new", views.AccountCreate.as_view(), name="account_create"),
    path("accounts/<pk>/", views.AccountDetail.as_view(), name="account_detail"),
    path("test/", views.test),
    path("transaction/product/", views.product_transaction, name="product_transaction"),
    path("transaction/custom/", views.custom_transaction, name="custom_transaction"),
    path("transaction/revert/", views.revert_transaction, name="revert_transaction"),
    path("transaction/events/", django_eventstream.urls.events, {"channels": ["transaction"]}, name="transaction_event"),
]
