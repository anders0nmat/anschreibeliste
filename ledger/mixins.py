from typing import Any, Dict, Literal, Optional, Type
from django.forms.forms import BaseForm
from django.http import HttpResponse
from django.views.generic.edit import FormMixin, ProcessFormView
from django.core.exceptions import ImproperlyConfigured
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.http.response import HttpResponseRedirect


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

class ExtraFormKwargsMixin(FormMixin):
    extra_form_kwargs = {}

    def get_form_kwargs(self):
        return super().get_form_kwargs() | self.extra_form_kwargs
    
class ContextQuerysetMixin(ContextMixin):
    querysets = {}
    
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return super().get_context_data(**kwargs) | {name: queryset.all() for name, queryset in self.querysets.items()}

class MultiFormMixin(ContextMixin):
    forms={}
    initial={}
    success_urls=None

    def get_forms(self) -> Dict[str, Any]:
        return self.forms
    
    def get_current_prefix(self) -> str | None:
        if hasattr(self, 'current_prefix'):
            return self.current_prefix
        for prefix in self.get_forms():
            if prefix in self.request.POST:
                return prefix
        return None
    
    def get_initial(self, prefix=None):
        if prefix is None:
            prefix = self.get_current_prefix()
        return self.initial.get(prefix, {}).copy()

    def get_form_kwargs(self, prefix=None):
        current_prefix = self.get_current_prefix()
        if prefix is None:
            prefix = current_prefix
        kwargs = {
            'initial': self.get_initial(prefix=prefix),
            'prefix': prefix,
        }

        if prefix == current_prefix and self.request.method in ("POST", "PUT"):
            kwargs |= {
                'data': self.request.POST,
                'files': self.request.FILES,
            }

        handler = getattr(self, f"get_{prefix}_form_kwargs", None)
        if callable(handler):
            kwargs = handler(**kwargs)

        return kwargs

    def get_form_class(self, prefix=None):
        if prefix is None:
            prefix = self.get_current_prefix()
        return self.get_forms()[prefix]

    def get_success_url(self, prefix=None):
        if self.success_urls is None:
            return None
        if isinstance(self.success_urls, Dict):
            if prefix is None:
                prefix = self.get_current_prefix()
            return self.success_urls[prefix]
        return self.success_urls


    
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        for prefix in self.get_forms():
            key = f"{prefix}_form"
            if key not in kwargs:
                self.current_prefix = prefix
                kwargs[key] = self.get_form(prefix=prefix)
                del self.current_prefix
        kwargs['form'] = None # To disable single-form mixins & views

        return super().get_context_data(**kwargs)
    
    def get_form(self, form_class=None, prefix=None):
        if form_class is None:
            form_class = self.get_form_class(prefix)
        return form_class(**self.get_form_kwargs(prefix=prefix))

    def form_valid(self, form):
        handler = getattr(self, f"{form.prefix}_valid", None)
        if callable(handler):
            return handler(form)
        return super().form_valid(form)

    def form_invalid(self, form):
        kwargs = {
            f"{form.prefix}_form": form
        }
        return self.render_to_response(self.get_context_data(**kwargs))


class BaseMultiFormView(MultiFormMixin, ProcessFormView):
    pass

class MultiFormView(TemplateResponseMixin, BaseMultiFormView):
    pass

class ExtraFormMixin(FormMixin):
    extra_forms = {}
    extra_initial = {}

    def get_extra_forms(self) -> Dict[str, BaseForm]:
        return self.extra_forms

    def get_extra_initial(self, name) -> Dict[str, Any]:
        return self.extra_initial.get(name, {}).copy()
    
    def get_extra_prefix(self, name) -> str | None:
        return None

    def get_extra_form_kwargs(self, name) -> Dict[str, Any]:
        kwargs = {
            'initial': self.get_extra_initial(name),
            'prefix': self.get_extra_prefix(name),
        }

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })

        func = getattr(self, f"get_{name}_form_kwargs", None)
        return func(**kwargs) if callable(func) else kwargs
    
    def get_current_name(self) -> str | None:
        for name in self.get_extra_forms():
            if name in self.request.POST:
                return name
        return None


    def get_form(self, form_class=None, name=None) -> BaseForm:
        if name is None:
            name = self.get_current_name()
        if name is not None:
            if form_class is None:
                form_class = self.get_extra_forms()[name]
            form = form_class(**self.get_extra_form_kwargs(name=name))
            form.name = name
            return form
        return super().get_form(form_class)
    
    def form_valid(self, form: Any) -> HttpResponse:
        if form.name in self.get_extra_forms():
            func = getattr(self, f"{form.name}_valid", None)
            if callable(func):
                return func(form)
            return HttpResponseRedirect(self.get_success_url())
        return super().form_valid(form)
    
    def form_invalid(self, form: Any) -> HttpResponse:
        if form.name in self.get_extra_forms():
            return self.render_to_response(self.get_context_data(**{f"{form.name}_form": form}))
        else:
            return super().form_invalid(form)
    
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        for name in self.get_extra_forms():
            key = f"{name}_form"
            if key not in kwargs:
                kwargs[key] = self.get_form(name=name)

        return super().get_context_data(**kwargs)
    
