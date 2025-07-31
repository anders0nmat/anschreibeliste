from typing import Self
from django.utils.translation import override as override_language
from django.conf import settings
from django.utils.formats import get_format
from django.utils.safestring import mark_safe

class server_language(override_language):
    """
    A context manager setting the currently active language to the server default.
    
    Usage:
    ```py
    with server_language():
        reason_message = _('User confirmed')
    ```
    """
    def __init__(self, deactivate: bool = False) -> None:
        super().__init__(settings.LANGUAGE_CODE, deactivate)


class fpint:
    __precision__ = 2
    __slots__ = ['value']

    def __init__(self, value: int | Self, negative: bool = None) -> None:    
        value = int(value)
        if negative is not None:
            value = -abs(value) if negative else abs(value)
        self.value = value

    def __int__(self) -> int:
        return self.value
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(value={self.value})"
    
    def __str__(self) -> str:
        return self._str('.')
    
    def __html__(self) -> str:
        negative, integer, fraction = self.parts
        classes = "money"
        if negative:
            classes += " negative"
        sign = '<span class="sign">-</span>' if negative else ''
        separator = get_format('DECIMAL_SEPARATOR')
        return mark_safe(f'''<span class="{classes}">{sign}<span class="integer">{integer}</span><span class="decimal-separator">{separator}</span><span class="fraction">{fraction:>0{self.__precision__}}</span></span>''')

    @property
    def locale_str(self) -> str:
        return self._str(get_format('DECIMAL_SEPARATOR'))
    
    def _str(self, separator: str) -> str:
        negative, integer, fraction = self.parts
        return f"{'-' if negative else ''}{integer}{separator}{fraction:>0{self.__precision__}}"

    @property
    def parts(self) -> tuple[bool, int, int]:
        return self.negative, *divmod(abs(self.value), 10 ** self.__precision__)
    
    @property
    def negative(self) -> bool:
        return self.value < 0
