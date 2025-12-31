from django.urls import path
from django.views.generic import ListView, DetailView

from .models import Recipe
from .views import recipe_edit, recipe_new

app_name = "blackbook"
urlpatterns = [
    path("", ListView.as_view(queryset=Recipe.objects.order_by('name')), name="recipes"),
    path("new/", recipe_new, name="recipe_new"),
    path("<pk>/", DetailView.as_view(model=Recipe), name="recipe"),
    path("<pk>/edit/", recipe_edit, name="recipe_edit"),
]

