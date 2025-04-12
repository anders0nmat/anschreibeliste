from django.db import models
from django.utils.translation import gettext as _

from . import formfield

class FixedPrecisionMixin:
    def __init__(self, *args, decimal_places: int, **kwargs) -> None:
        self.decimal_places = decimal_places
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['decimal_places'] = self.decimal_places
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {
            'form_class': formfield.FixedPrecisionField,
            'decimal_places': self.decimal_places
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

class FixedPrecisionField(FixedPrecisionMixin, models.BigIntegerField):
    """
    Integer field represented as a fixed precision decimal number in forms
    """
    description = _('Fixed precision decimal (up to %(decimal_places)i decimal places)')    

class PositiveFixedPrecisionField(FixedPrecisionMixin, models.PositiveBigIntegerField):
    """
    Positive integer field represented as a fixed precision decimal number in forms
    """
    description = _('Positive fixed precision decimal (up to %(decimal_places)i decimal places)')
    
