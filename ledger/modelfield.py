from typing import Any
from django.db import models
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError

from . import formfield

class FixedPrecisionField(models.BigIntegerField):
    description = _('Fixed precision decimal (up to %(decimal_places)i decimal places)')
    def __init__(self, *args: Any, decimal_places: int, **kwargs: Any) -> None:
        self.decimal_places = decimal_places
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> Any:
        name, path, args, kwargs = super().deconstruct()
        kwargs['decimal_places'] = self.decimal_places
        return name, path, args, kwargs

    def formfield(self, **kwargs: Any) -> Any:
        defaults = {
            'form_class': formfield.FixedPrecisionField,
            'decimal_places': self.decimal_places
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
    

class PositiveFixedPrecisionField(models.PositiveBigIntegerField):
    description = _('Positive fixed precision decimal (up to %(decimal_places)i decimal places)')

    def __init__(self, *args: Any, decimal_places: int, **kwargs: Any) -> None:
        self.decimal_places = decimal_places
        super().__init__(*args, **kwargs)
        
    def deconstruct(self) -> Any:
        name, path, args, kwargs = super().deconstruct()
        kwargs['decimal_places'] = self.decimal_places
        return name, path, args, kwargs

    def formfield(self, **kwargs: Any) -> Any:
        defaults = {
            'form_class': formfield.FixedPrecisionField,
            'decimal_places': self.decimal_places
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
    
