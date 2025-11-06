from django.db import models
from django.utils.translation import gettext_lazy as _

from ledger.models import Product

# Create your models here.

class ServingGlass(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)

    def __str__(self) -> str:
        return self.name

class PrepMethod(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)

    def __str__(self) -> str:
        return self.name

class RecipeGroup(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)

    def __str__(self) -> str:
        return self.name

class Recipe(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)
    description = models.TextField(verbose_name=_('description'), blank=True)

    group = models.ForeignKey(RecipeGroup, on_delete=models.SET_NULL, null=True, blank=True, default=None)

    serving_glass = models.ForeignKey(ServingGlass, on_delete=models.SET_NULL, null=True, blank=True, default=None)
    method = models.ForeignKey(PrepMethod, on_delete=models.SET_NULL, null=True, blank=True, default=None)

    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, default=None)

    steps: models.QuerySet["RecipeStep"]

    def __str__(self) -> str:
        return self.name
    
    class Meta:
        ordering = ['group', 'name']

class Unit(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)
    format = models.CharField(verbose_name=_('format'), max_length=255)

    def __str__(self) -> str:
        return self.name

class IngredientCategory(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)

    def __str__(self) -> str:
        return self.name

class Ingredient(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)
    category = models.ForeignKey(IngredientCategory, on_delete=models.SET_NULL, null=True, blank=True, default=None)

    def __str__(self) -> str:
        return self.name

class RecipeStep(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='steps')
    order = models.PositiveIntegerField(
        verbose_name=_('order'),
        default=0,
        blank=False,
        null=False,
        db_index=True
    )

    amount = models.DecimalField(verbose_name=_('amount'), max_digits=5, decimal_places=2, null=True, blank=True, default=None)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True, default=None)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, null=True, blank=True, default=None)
    instruction = models.CharField(verbose_name=_('instruction'), max_length=255, blank=True)

    class Meta:
        ordering = ['recipe', 'order']
        indexes = [
            models.Index(models.F('recipe'), 'order', name="idx_recipe_order")
        ]


    def formatted_amount(self) -> str:
        if self.amount is not None:
            amount = str(self.amount).strip('0')
            if amount.startswith('.'):
                amount = '0' + amount
            if amount.endswith('.'):
                amount = amount[:-1]
            if amount == '':
                amount = '0'
        else:
            amount = ''

        return self.unit.format.format(amount=amount)

    def __str__(self) -> str:
        s = f"{self.recipe.name} > ({self.order})"

        if self.unit is not None:
            amount = str(self.amount) if self.amount is not None else ''
            s += f" {self.unit.format.format(amount=amount)}"
        if self.ingredient is not None:
            s += f" {self.ingredient.name}"

        s += f" {self.instruction}"
        return s

