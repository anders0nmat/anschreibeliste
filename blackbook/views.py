from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse
from django.forms import modelform_factory, inlineformset_factory

from .models import Recipe, RecipeStep

# Create your views here.

def recipe_edit(request: HttpRequest, pk):
    RecipeForm = modelform_factory(Recipe, fields='__all__')
    RecipeStepFormset = inlineformset_factory(Recipe, RecipeStep, fields='__all__')

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
        formset = RecipeStepFormset(instance=recipe)

        return render(request, 'blackbook/recipe_form.html', {
            'form': form,
            'formset': formset,
        })