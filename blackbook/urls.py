from django.urls import path
from django.views.generic import TemplateView, ListView, DetailView, UpdateView

from .models import Recipe
from .views import recipe_edit

app_name = "blackbook"
urlpatterns = [
    path("", ListView.as_view(model=Recipe), name="recipes"),
    path("<pk>/", DetailView.as_view(model=Recipe), name="recipe"),
    path("<pk>/edit/", recipe_edit, name="recipe_edit"),
]