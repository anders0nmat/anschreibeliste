from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from colorfield.fields import ColorField

from ledger.models import Product

# Create your models here.

class NamedModel(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.name

class ServingGlass(NamedModel):
    icon = models.TextField(default="", blank=True)

    class Meta:
        verbose_name = _("Serving glass")
        verbose_name_plural = _("Serving glasses")

class PrepMethod(NamedModel):
    icon = models.TextField(default="", blank=True)

    class Meta:
        verbose_name = _("Prep method")
        verbose_name_plural = _("Prep methods")
    
class IngredientCategory(NamedModel):
    light_color = ColorField(verbose_name=_('Light Color'), null=True, blank=True, default=None)
    dark_color = ColorField(verbose_name=_('Dark Color'), null=True, blank=True, default=None)

    class Meta:
        verbose_name = _("Ingredient category")
        verbose_name_plural = _("Ingredient categories")

class Ingredient(NamedModel):
    category = models.ForeignKey(IngredientCategory, on_delete=models.SET_NULL, null=True, blank=True, default=None)

    class Meta:
        verbose_name = _("Ingredient")
        verbose_name_plural = _("Ingredients")

class RecipeGroup(NamedModel):
    order = models.PositiveIntegerField(
        verbose_name=_('order'),
        default=0,
        blank=False,
        null=False,
        db_index=True
    )

    class Meta:
        verbose_name = _("Recipe Group")
        verbose_name_plural = _("Recipe Groups")
        ordering = ['order']

class Recipe(NamedModel):
    description = models.TextField(verbose_name=_('description'), blank=True)

    group = models.ForeignKey(RecipeGroup, verbose_name=_('group'), on_delete=models.SET_NULL, null=True, blank=True, default=None)

    serving_glass = models.ForeignKey(ServingGlass, verbose_name=_('Glass'), on_delete=models.SET_NULL, null=True, blank=True, default=None)
    method = models.ForeignKey(PrepMethod, verbose_name=_('method'), on_delete=models.SET_NULL, null=True, blank=True, default=None)

    product = models.ForeignKey(Product, verbose_name=_('Product'), on_delete=models.SET_NULL, null=True, blank=True, default=None, help_text=_("Used to display pricing"))

    steps: models.QuerySet["RecipeStep"]
    
    class Meta:
        verbose_name = _("Recipe")
        verbose_name_plural = _("Recipes")
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
        verbose_name = _("Recipe step")
        verbose_name_plural = _("Recipe steps")
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

