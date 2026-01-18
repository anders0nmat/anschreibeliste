from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponseRedirect

from .models import Recipe, Tag
from .forms import RecipeForm, RecipeStepFormset, TagFormset

# Create your views here.

def recipe_edit(request: HttpRequest, pk):
    recipe = None
    if pk is not None:
        recipe = get_object_or_404(Recipe, pk=pk)

    if request.method == "POST":
        form = RecipeForm(request.POST, instance=recipe)
        formset = RecipeStepFormset(request.POST, instance=recipe)
        tag_formset = TagFormset(request.POST, prefix="new-tags", queryset=Tag.objects.none())

        if form.is_valid() and formset.is_valid():
            recipe: Recipe = form.save()
            formset.instance = recipe
            formset.save()

            if tag_formset.is_valid():
                new_tags = tag_formset.save()
                recipe.tags.add(*new_tags)
                recipe.save()

            return HttpResponseRedirect(recipe.get_absolute_url())

        formset.remove_temporary()
    else:
        form = RecipeForm(instance=recipe)
        formset = RecipeStepFormset(instance=recipe)
        tag_formset = TagFormset(prefix="new-tags", queryset=Tag.objects.none())

    return render(request, 'blackbook/recipe_form.html', {
        'form': form,
        'formset': formset,
        'tag_formset': tag_formset,
    })

