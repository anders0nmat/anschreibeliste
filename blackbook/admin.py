from django.contrib import admin

from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminBase, SortableAdminMixin

from . import models, forms

# Register your models here.

admin.site.register(models.Ingredient)
admin.site.register(models.IngredientCategory)
admin.site.register(models.PrepMethod, form=forms.PrepMethodForm)
admin.site.register(models.ServingGlass, form=forms.ServingGlassForm)

@admin.register(models.RecipeGroup)
class RecipeGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ['name']

class RecipeStepInline(SortableInlineAdminMixin, admin.TabularInline):
    model = models.RecipeStep
    ordering = ['order']

@admin.register(models.Recipe)
class RecipeAdmin(SortableAdminBase, admin.ModelAdmin):
    inlines = [RecipeStepInline]
