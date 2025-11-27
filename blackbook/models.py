from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from ledger.models import Product

# Create your models here.

class NamedModel(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.name

class ServingGlass(NamedModel): pass
class PrepMethod(NamedModel): pass
class IngredientCategory(NamedModel): pass

class Ingredient(NamedModel):
    category = models.ForeignKey(IngredientCategory, on_delete=models.SET_NULL, null=True, blank=True, default=None)

class RecipeGroup(NamedModel):
    order = models.PositiveIntegerField(
        verbose_name=_('order'),
        default=0,
        blank=False,
        null=False,
        db_index=True
    )

    class Meta:
        ordering = ['order']

class Recipe(NamedModel):
    description = models.TextField(verbose_name=_('description'), blank=True)

    group = models.ForeignKey(RecipeGroup, on_delete=models.SET_NULL, null=True, blank=True, default=None)

    serving_glass = models.ForeignKey(ServingGlass, on_delete=models.SET_NULL, null=True, blank=True, default=None)
    method = models.ForeignKey(PrepMethod, on_delete=models.SET_NULL, null=True, blank=True, default=None)

    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, default=None)

    steps: models.QuerySet["RecipeStep"]
    
    class Meta:
        ordering = ['group__order', 'name']

    def get_absolute_url(self) -> str:
        return reverse('blackbook:recipe', kwargs={'pk': self.pk})

class RecipeStep(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='steps')
    order = models.PositiveIntegerField(
        verbose_name=_('order'),
        default=0,
        blank=False,
        null=False,
        db_index=True
    )

    amount = models.CharField(verbose_name=_('amount'), max_length=64, blank=True, default="")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, null=True, blank=True, default=None)
    instruction = models.CharField(verbose_name=_('instruction'), max_length=255, blank=True)

    class Meta:
        ordering = ['recipe', 'order']
        indexes = [
            models.Index(models.F('recipe'), 'order', name="idx_recipe_order")
        ]

    def __str__(self) -> str:
        s = f"{self.recipe.name}.{self.order}:"

        if self.ingredient:
            s += f" {self.amount} {self.ingredient.name}"

        s += f" {self.instruction}"
        return s.strip()

