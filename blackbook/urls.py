from django.urls import path
from django.views.generic import TemplateView, ListView, DetailView

from .models import Recipe

app_name = "blackbook"
urlpatterns = [
    path("", ListView.as_view(model=Recipe), name="recipes"),
    path("recipe/<pk>/", DetailView.as_view(model=Recipe), name="recipe"),
]