from django.urls import path
from .views import recipe_edit, RecipeList, RecipeDetail

app_name = "blackbook"
urlpatterns = [
    path("", RecipeList.as_view(), name="recipes"),
    path("new/", recipe_edit, name="recipe_new", kwargs={'pk': None}),
    path("<pk>/", RecipeDetail.as_view(), name="recipe"),
    path("<pk>/edit/", recipe_edit, name="recipe_edit"),
]

