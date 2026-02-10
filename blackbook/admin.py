from django.contrib import admin

from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminBase, SortableAdminMixin
from django_admin_action_forms import action_with_form, AdminActionForm, AdminActionFormsMixin
from django.forms import ModelChoiceField, ModelMultipleChoiceField
from django.contrib import messages
from . import models, forms
from django.utils.translation import gettext_lazy as _
# Register your models here.

class IngredientAssignCategory(AdminActionForm):
    category = ModelChoiceField(models.IngredientCategory.objects.all())

@admin.register(models.Ingredient)
class IngredientAdmin(AdminActionFormsMixin, admin.ModelAdmin):
    list_display = ['name', 'category']
    ordering = ['category__name', 'name']

    @action_with_form(IngredientAssignCategory, description='Assign ingredients to category')
    def assign_ingredient_category(self, request, queryset, data):
        category = data['category']
        queryset.update(category=category)
        self.message_user(request, f'Successfully assigned category {category.name} to {queryset.count()} ingredients', level=messages.SUCCESS)

    actions = [assign_ingredient_category]

admin.site.register(models.IngredientCategory)
admin.site.register(models.PrepMethod, form=forms.PrepMethodForm)
admin.site.register(models.ServingGlass, form=forms.ServingGlassForm)

admin.site.register(models.Tag)

@admin.register(models.RecipeGroup)
class RecipeGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ['name']

class RecipeStepInline(SortableInlineAdminMixin, admin.TabularInline):
    model = models.RecipeStep
    ordering = ['order']

class RecipeAssignCategory(AdminActionForm):
    group = ModelChoiceField(models.RecipeGroup.objects.all())

class RecipeAssignTags(AdminActionForm):
    add_tags = ModelMultipleChoiceField(models.Tag.objects.all(), label=_('Add tags'), required=False)
    remove_tags = ModelMultipleChoiceField(models.Tag.objects.all(), label=_('Remove tags'), required=False)

    class Meta:
        filter_horizontal = ['add_tags', 'remove_tags']

@admin.register(models.Recipe)
class RecipeAdmin(AdminActionFormsMixin, SortableAdminBase, admin.ModelAdmin):
    inlines = [RecipeStepInline]
    list_display = ['name', 'group', 'tag_list']
    filter_horizontal = ('tags', )

    @admin.display(description=_('Tags'))
    def tag_list(self, obj: models.Recipe):
        tags = obj.tags.values_list('name', flat=True)
        return ', '.join(tags)
    
    @action_with_form(
        RecipeAssignCategory,
        description=_('Assign recipe group to selected recipes')
    )
    def assign_group(self, request, queryset, data):
        queryset.update(group=data['group'])
        self.message_user(request, f'Successfully assigned recipe group "{data["group"].name}" to {queryset.count()} recipes', level=messages.SUCCESS)

    @action_with_form(
        RecipeAssignTags,
        description=_('Manage tags of selected recipes')
    )
    def assign_tags(self, request, queryset, data):
        recipe: models.Recipe
        for recipe in queryset:
            recipe.tags.add(*data['add_tags'])
            recipe.tags.remove(*data['remove_tags'])

    actions = [assign_group, assign_tags]
