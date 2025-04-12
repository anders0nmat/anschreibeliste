from typing import Literal
from django.views.generic.edit import FormMixin
from django.core.exceptions import ImproperlyConfigured


class EnableFieldsMixin(FormMixin):
    enabled_fields = None
    disabled_fields = None
    
    def get_enabled_fields(self) -> list[str] | Literal['__all__']:
        return self.enabled_fields
    
    def get_disabled_fields(self) -> list[str] | Literal['__all__']:
        return self.disabled_fields
    
    def get_form(self, form_class = None):
        form = super().get_form(form_class)

        enabled_fields = self.get_enabled_fields()
        disabled_fields = self.get_disabled_fields()

        if enabled_fields and disabled_fields:
            raise ImproperlyConfigured("Defined both enabled_fields and disabled_fields. Can only define one")
        if enabled_fields is None and disabled_fields is None:
            raise ImproperlyConfigured("Defined neither enabled_fields nor disabled_fields. Need to define exactly one")

        if enabled_fields:
            if enabled_fields == '__all__':
                disabled_fields = []
            else:
                disabled_fields = form.fields.keys() - set(enabled_fields)
        
        if disabled_fields == '__all__':
            disabled_fields = form.fields.keys()
        disabled_fields = set(disabled_fields) & form.fields.keys()

        for field in disabled_fields:
            form.fields[field].disabled = True
        
        setattr(form, 'has_enabled_fields', disabled_fields < form.fields.keys())
        return form
