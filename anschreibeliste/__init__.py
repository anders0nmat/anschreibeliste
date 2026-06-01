from typing import Any, Mapping, Optional, Type, Union
from django.forms import BaseForm
from django.forms.utils import ErrorList

old_init = BaseForm.__init__

def new_base_form_init(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,
        initial=None,
        error_class=ErrorList,
        label_suffix=None,
        empty_permitted=False,
        field_order=None,
        use_required_attribute=None,
        renderer=None,
        bound_field_class=None,
):
    old_init(
        self,
        data,
        files,
        auto_id,
        prefix,
        initial,
        error_class,
        label_suffix if label_suffix is not None else '',
        empty_permitted,
        field_order,
        use_required_attribute,
        renderer,
        bound_field_class)

BaseForm.__init__ = new_base_form_init

