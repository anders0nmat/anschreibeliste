from django.contrib import admin

from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminBase

from . import models

# Register your models here.

admin.site.register(models.Ingredient)
admin.site.register(models.IngredientCategory)
admin.site.register(models.PrepMethod)
admin.site.register(models.ServingGlass)
admin.site.register(models.Unit)
admin.site.register(models.RecipeGroup)

class RecipeStepInline(SortableInlineAdminMixin, admin.TabularInline):
    model = models.RecipeStep
    ordering = ['order']

@admin.register(models.Recipe)
class RecipeAdmin(SortableAdminBase, admin.ModelAdmin):
    inlines = [RecipeStepInline]
