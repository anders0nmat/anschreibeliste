from typing import Any
from django import forms
from django.forms.widgets import Widget, NumberInput, Input
from django.utils.formats import sanitize_separators, number_format, get_format
from django.utils.translation import gettext as _
from re import escape

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

            if isinstance(self.widget, DecimalInput):
                formatting = f"{sign}{wholes}.{cents:>0{self.decimal_places}}"
                return number_format(formatting, self.decimal_places)
            else:
                if cents == 0:
                    formatting = f"{sign}{wholes}"
                else:
                    formatting = f"{sign}{wholes}.{cents:>0{self.decimal_places}}"
                return formatting
        return value

    def to_python(self, value: Any | None) -> int | None:
        if value in self.empty_values:
            return None
        
        WHOLES_FACTOR = 10 ** self.decimal_places
        
        if isinstance(value, str):
            value = value.strip()
            negative, value = value.startswith('-'), value.removeprefix('-')
            value = sanitize_separators(value)
            wholes, _, cents = value.partition('.')
            cents = cents.ljust(self.decimal_places, '0')
            wholes = wholes.rjust(1, '0')
        elif isinstance(value, int):
            negative, wholes, cents = value < 0, abs(value), 0
        elif isinstance(value, float):
            negative, value = value < 0, int(abs(value) * WHOLES_FACTOR)
            wholes, cents = divmod(value, WHOLES_FACTOR)
        else:
            negative, wholes, cents = value < 0, abs(value), 0
        
        try:
            wholes = int(wholes) * WHOLES_FACTOR
            cents = int(cents)
            if cents >= 10 ** self.decimal_places:
                raise ValueError()
        except ValueError:
            raise forms.ValidationError(self.error_messages['invalid'].format(decimal_places=self.decimal_places), code='invalid')
        
        amount = wholes + cents
        return -amount if negative else amount
    
    def widget_attrs(self, widget: Widget) -> Any:
        attrs = super().widget_attrs(widget)
        if isinstance(widget, NumberInput) and "step" not in widget.attrs:
            step = f"1e-{self.decimal_places}"
            attrs.setdefault('step', step)
        if isinstance(widget, DecimalInput) and "pattern" not in widget.attrs:
            decimal_separator = get_format('DECIMAL_SEPARATOR')
            pattern = '\\d+'
            if self.decimal_places > 0:
                pattern += f'([{escape(decimal_separator)}.]\\d{{1,{self.decimal_places}}})?'
            attrs.setdefault('pattern', pattern)
        return attrs

