from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "wiki"
urlpatterns = [
    path('', views.article_detail, kwargs={'slug': '_start'}, name="main"),

    path(':/', RedirectView.as_view(permanent=True, pattern_name="article_create"), kwargs={'slug': ':'}),
    path(':/edit/', views.article_update, kwargs={'slug': None}, name="article_create"),
    path('<slug:slug>/', views.article_detail, name="article_detail"),
    path('<slug:slug>/edit/', views.article_update, name="article_update"),
    path('<slug:slug>/taskitem/', views.article_checkbox),
    path('<slug:slug>/files/', views.article_attachment_list, name="article_attachment_list"),
    path('<slug:slug>/files/<str:name>', views.article_attachment, name="article_attachment"),

    path(':/edit/preview', views.article_preview, name="article_preview"),
]
