from django.urls import path
from django.views.generic import ListView, DetailView

from .models import Recipe
from .views import recipe_edit

app_name = "blackbook"
urlpatterns = [
    path("", ListView.as_view(queryset=Recipe.objects.order_by('name')), name="recipes"),
    path("new/", recipe_edit, name="recipe_new", kwargs={'pk': None}),
    path("<pk>/", DetailView.as_view(model=Recipe), name="recipe"),
    path("<pk>/edit/", recipe_edit, name="recipe_edit"),
]

