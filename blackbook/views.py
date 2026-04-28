from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponseRedirect
from django.views.generic import ListView, DetailView

from .models import Recipe, Tag, RecipeStep
from .forms import RecipeForm, RecipeStepFormset, TagFormset

# Create your views here.

class RecipeList(ListView):
    queryset = Recipe.objects\
        .only('name', 'group')\
        .order_by('name')\
        .select_related('group')\
        .prefetch_related('tags', 'steps__ingredient')

class RecipeDetail(DetailView):
    queryset = Recipe.objects\
        .select_related('group', 'serving_glass', 'method', 'product')\
        .prefetch_related('steps__ingredient', 'tags')

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
        from django.forms.models import model_to_dict
        import re
        form_initial = formset_initial = None

        clone = request.GET.get('clone')
        if clone:
            clone = get_object_or_404(Recipe, pk=clone)
            regex = re.compile(r"^(.*?)(?:\s+(\d+))?$")
            clone_name, _ = regex.findall(clone.name)[0]

            similar_names: list[str] = Recipe.objects.filter(name__startswith=clone_name).values_list('name', flat=True)

            highest_number = max((int(regex.findall(name)[0][1] or '1') for name in similar_names), default=1)

            clone.name = clone_name + ' ' + str(highest_number + 1)

            form_initial = model_to_dict(clone)
            formset_initial = [model_to_dict(step, exclude=['id', 'recipe']) for step in clone.steps.all()]

        form = RecipeForm(instance=recipe, initial=form_initial)
        class RecipeStepFormsetExtra(RecipeStepFormset):
            extra = len(formset_initial or []) + RecipeStepFormset.extra
        formset = RecipeStepFormsetExtra(instance=recipe, initial=formset_initial)
        tag_formset = TagFormset(prefix="new-tags", queryset=Tag.objects.none())


    return render(request, 'blackbook/recipe_form.html', {
        'form': form,
        'formset': formset,
        'tag_formset': tag_formset,
    })

