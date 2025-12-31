from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse
from django.forms import inlineformset_factory

from .models import Recipe, RecipeStep
from .forms import RecipeForm

# Create your views here.

RecipeStepFormset = inlineformset_factory(Recipe, RecipeStep, fields='__all__')

RecipeForm.base_fields['name'].widget.attrs['placeholder'] = ' '
RecipeForm.base_fields['description'].widget.attrs['placeholder'] = ' '


def recipe_new(request: HttpRequest):
    if request.method == "POST":
        form = RecipeForm(request.POST)

        if form.is_valid():
            recipe = form.save()

            formset = RecipeStepFormset(request.POST, instance=recipe)
            if formset.is_valid():
                formset.save()
            else:
                return HttpResponse(form.errors.as_text() + '\n' + '\n'.join(e.as_text() for e in formset.errors))
        else:
            return HttpResponse(form.errors.as_text() + '\n' + '\n'.join(e.as_text() for e in formset.errors))
        
        return HttpResponseRedirect(recipe.get_absolute_url())
    else:
        RecipeForm.base_fields['description'].widget.attrs['rows'] = '3'

        form = RecipeForm(label_suffix='')
        formset = RecipeStepFormset(form_kwargs={'label_suffix': ''})

        return render(request, 'blackbook/recipe_form.html', {
            'form': form,
            'formset': formset,
        })

def recipe_edit(request: HttpRequest, pk):
    if request.method == "POST":
        recipe = get_object_or_404(Recipe, pk=pk)
        form = RecipeForm(request.POST, instance=recipe)
        formset = RecipeStepFormset(request.POST, instance=recipe)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
        else:
            return HttpResponse(form.errors.as_text() + '\n' + '\n'.join(e.as_text() for e in formset.errors))
        
        return HttpResponseRedirect(recipe.get_absolute_url())
    else:
        recipe = get_object_or_404(Recipe, pk=pk)
        RecipeForm.base_fields['description'].widget.attrs['rows'] = '3'

        form = RecipeForm(instance=recipe, label_suffix='')
        formset = RecipeStepFormset(instance=recipe, form_kwargs={'label_suffix': ''})

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
