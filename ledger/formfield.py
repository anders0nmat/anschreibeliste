from typing import Any, Optional, Literal
from django import forms
from django.forms.widgets import Widget, NumberInput, Input
from django.utils.formats import sanitize_separators, number_format, get_format
from django.utils.translation import gettext as _

class DecimalInput(Input):
    input_type = 'text'
    template_name = 'django/forms/widgets/text.html'

    def __init__(self, attrs=None) -> None:
        default_attrs = {"inputmode": "decimal"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

class FixedPrecisionField(forms.IntegerField):
    widget = DecimalInput
    
    default_error_messages = {
        'invalid': _('Enter a number with {decimal_places} decimal places.'),
    }

    def __init__(self, *, decimal_places: int, **kwargs) -> None:
        self.decimal_places = decimal_places
        super().__init__(**kwargs)

    def prepare_value(self, value: Any) -> Any:
        if isinstance(value, int):
            sign, value = '-' if value < 0 else '', abs(value)
            wholes, cents = divmod(value, 10 ** self.decimal_places)
            if cents == 0: return number_format(wholes)
            cents = str(cents).rjust(self.decimal_places, '0')
            return f"{sign}{wholes}.{cents}"
        return value

    def to_python(self, value: Any | None) -> int | None:
        if value in self.empty_values:
            return None
        
        value = sanitize_separators(value)
        if isinstance(value, str):
            wholes, cents, *_ = value.split('.', maxsplit=1) + ['0']
            cents = cents.ljust(self.decimal_places, '0')
        else:
            wholes, cents = value, 0

        try:
            wholes = int(wholes) * (10 ** self.decimal_places)
            cents = int(cents)
            if cents >= 10 ** self.decimal_places:
                raise ValueError()
        except ValueError:
            raise forms.ValidationError(self.error_messages['invalid'].format(decimal_places=self.decimal_places), code='invalid')
        
        return wholes + cents
    
    def widget_attrs(self, widget: Widget) -> Any:
        attrs = super().widget_attrs(widget)
        if isinstance(widget, NumberInput) and "step" not in widget.attrs:
            step = f"1e-{self.decimal_places}"
            attrs.setdefault('step', step)
        if isinstance(widget, DecimalInput) and "pattern" not in widget.attrs:
            decimal_separator = get_format('DECIMAL_SEPARATOR')
            pattern = '\\d+'
            if self.decimal_places > 0:
                pattern += '('
                pattern += '[' + ('\\\\' if decimal_separator == '\\' else decimal_separator) + '.]'
                pattern += f'\\d{{1,{self.decimal_places}}}'
                pattern += ')?'
            attrs.setdefault('pattern', pattern)
        return attrs

class DisabledFieldMixin:
    def __init__(self, *args, disabled_fields: list[str] | Literal['__all__'] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if disabled_fields is None:
            disabled_fields = set()
        elif disabled_fields == '__all__':
            disabled_fields = set(self.fields.keys())
        else:
            disabled_fields = set(field for field in disabled_fields if field in self.fields)

        for disabled_field in disabled_field:
            self.fields[disabled_field].disabled = True

        self.has_enabled_fields = disabled_fields < self.fields.keys()


