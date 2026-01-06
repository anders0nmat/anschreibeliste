from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponseRedirect

from .models import Recipe
from .forms import RecipeForm, RecipeStepFormset

# Create your views here.

def recipe_edit(request: HttpRequest, pk):
    recipe = None
    if pk is not None:
        recipe = get_object_or_404(Recipe, pk=pk)

    if request.method == "POST":
        form = RecipeForm(request.POST, instance=recipe)
        formset = RecipeStepFormset(request.POST, instance=recipe)

        if form.is_valid() and formset.is_valid():
            recipe: Recipe = form.save()
            formset.instance = recipe
            formset.save()
            return HttpResponseRedirect(recipe.get_absolute_url())
    
        formset.remove_temporary()
    else:
        form = RecipeForm(instance=recipe)
        formset = RecipeStepFormset(instance=recipe)

    return render(request, 'blackbook/recipe_form.html', {
        'form': form,
        'formset': formset,
    })

def recipe_search():
    """
    Feature-rich search for recipes.

    space separated queries, prefix separated by ":"

    example: "fresh has:tomat tag:fizz"

    Looking for a entry containing:
    - the string "fresh",
    - a step using a ingredient containing the string "tomat"
    - a tag containing the string "fizz"
    """
    ...
