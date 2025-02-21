from django import template
from django.utils.safestring import mark_safe
from typing import Any

register = template.Library()

@register.filter("money")
def money(value):
    """
    Format a number representing currency in a html span to allow for custom styling
    
    If value is not of type `int`, it is returned without modification. 
    Otherwise, `value` is interpreted as cents, so `value == 100` equals one unit of currency (e.g. $1)

    No assumption is made about the kind of currency handled, in particular, 
    no currency-symbol is added to the result. This may be done by css-styling
    using the `::after`-pseudo-selector.
    
    It is then brought in the following html structure:
    ```html
    <span class="money" [negative]>
        <span class="wholes">{wholes}</span>
        <span class="cents">{cents}</span>
    </span>
    ```

    The `negative`-attribute is set on the `money`-span if `value < 0`.
    The cents are '0'-padded to two digits.

    Example use:
    ```html
    <div>
        {{ -2309|money }}
    </div>
    ```
    Would result in:
    ```html
    <div>
        <span class="money" negative>
            <span class="wholes">23</span>
            <span class="cents">09</span>
        </span>
    </div>
    ```
    """

    if isinstance(value, int):
        value: int # Type hint for IDE
        neg, value = value < 0, abs(value)
        wholes, cents = divmod(value, 100)
        sign = "negative" if neg else ""
        
        return mark_safe(f'<span class="money" {sign}><span class="wholes">{wholes}</span><span class="cents">{cents:02d}</span></span>')
    return value

@register.simple_tag(name="ensure_group_leading")
def ensure_leading_with(group_list: list[tuple[Any, Any]], *, grouper):
    if not isinstance(group_list, list):
        print(f"{group_list=}")
        return None
    if not group_list:
        return [(grouper, [])]
    if group_list[0][0] != grouper:
        return [(grouper, [])] + group_list
    return group_list
