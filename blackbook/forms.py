
from typing import Any, Callable, Iterator, Tuple
from django.forms import ModelForm, ModelChoiceField, FileField, ValidationError,  TextInput, BaseInlineFormSet, inlineformset_factory, CheckboxInput
from itertools import groupby
from io import BytesIO
from django.core.files.uploadedfile import UploadedFile

from django.utils.safestring import SafeText, mark_safe
from ledger.models import Product
from .models import Recipe, ServingGlass, PrepMethod, RecipeStep, Ingredient
from django.utils.translation import gettext_lazy as _

import xml.etree.ElementTree as ET

from base.forms import NoLabelSuffixMixin

class GroupedModelChoiceIterator(ModelChoiceField.iterator):
    def __iter__(self) -> Iterator[Tuple[int | str, str]]:
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        for group, choices in groupby(
            self.queryset.all(),
            key=lambda row: getattr(row, self.field.group_by_field)
        ):
            if group is not None:
                yield (
                    self.field.group_label(group),
                    [self.choice(ch) for ch in choices]
                )

class GroupedModelChoiceField(ModelChoiceField):
    iterator = GroupedModelChoiceIterator

    def __init__(self, *args, group_by_field: str, group_label: Callable[[Any], str]=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.group_by_field = group_by_field
        if group_label is None:
            self.group_label = lambda x: x
        else:
            self.group_label = group_label

class RecipeForm(NoLabelSuffixMixin, ModelForm):
    class Meta:
        model = Recipe
        fields = '__all__'
    
    product = GroupedModelChoiceField(Product.objects.filter(category=Product.ProductCategory.ARTICLE), group_by_field='group', group_label=lambda group: group.name, label=_('product'), required=False, help_text=_("Used to display pricing"))

RecipeForm.base_fields['name'].widget.attrs['placeholder'] = ' '
RecipeForm.base_fields['description'].widget.attrs['placeholder'] = ' '
RecipeForm.base_fields['description'].widget.attrs['rows'] = '3'

def clean_svg(svg: str, file: UploadedFile | None=None) -> str:
    if file:
        if file.content_type == 'image/svg+xml':
            new_data = BytesIO()
            for chunk in file.chunks():
                new_data.write(chunk)
            new_data.seek(0)
            element = ET.parse(new_data).getroot()
        else:
            raise ValidationError('Unknown mime type', 'invalid_mime_type')
    else:
        try:
            element = ET.fromstring(svg)
        except:
            raise ValidationError('Invalid SVG code', 'invalid_svg')
    
    # Remove all <script> tags
    for script_tag in element.iter('script'):
        element.remove(script_tag)

    # Remove all svg namespace
    for node in element.iter():
        node.tag = node.tag.removeprefix('{http://www.w3.org/2000/svg}')

    return ET.tostring(element, encoding="unicode", method="html", xml_declaration=False)

class ServingGlassForm(ModelForm):
    class Meta:
        model = ServingGlass
        fields = '__all__'
    
    icon_file = FileField(required=False, label="Icon from file")
    
    def clean_icon(self):
        return clean_svg(self.cleaned_data['icon'], self.files.get('icon_file'))

class PrepMethodForm(ModelForm):
    class Meta:
        model = PrepMethod
        fields = '__all__'
    
    icon_file = FileField(required=False, label="Icon from file")
    
    def clean_icon(self):
        return clean_svg(self.cleaned_data['icon'], self.files.get('icon_file'))

class TextChoiceWidget(TextInput):
    def __init__(self, choices=(), datalist_id=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.choices = choices
        self.datalist_id = datalist_id

    def get_value_name(self, value):
        for option_value, option_label in self.choices:
            if isinstance(option_label, (list, tuple)):
                for subvalue, sublabel in option_label:
                    if subvalue.instance.pk == value:
                        return sublabel
            else:
                if option_value.instance.pk == value:
                    return option_label
        return value
    
    def render(self, name, value, attrs=None, renderer=None) -> SafeText:
        list_id = self.datalist_id or f"{name}-list"
        attrs.setdefault('list', list_id)
        data_list = ""
        if not self.datalist_id:
            data_list = f'<datalist id="{list_id}">'
            for option_value, option_label in self.choices:
                if isinstance(option_label, (list, tuple)):
                    data_list += f'<optgroup label="{option_value}">'
                    for subvalue, sublabel in option_label:
                        data_list += f'<option value="{sublabel}">'
                    data_list += f'</optgroup>'
                else:
                    data_list += f'<option value="{option_label}">'
                    
            data_list += f'</datalist>'
        
        # Find proper label for value
        value = self.get_value_name(value)

        html = super().render(name, value, attrs, renderer)
        return mark_safe(html + data_list)

    def datalist(self) -> SafeText:
        data_list = f'<datalist id="{self.datalist_id}">'
        for option_value, option_label in self.choices:
            if isinstance(option_label, (list, tuple)):
                data_list += f'<optgroup label="{option_value}">'
                for _, sublabel in option_label:
                    data_list += f'<option value="{sublabel}">'
                data_list += f'</optgroup>'
            else:
                data_list += f'<option value="{option_label}">'
                
        data_list += f'</datalist>'
        return mark_safe(data_list)

class AutoCreateModelField(ModelChoiceField):
    def __init__(self, *args, defaults=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.defaults = defaults

    def to_python(self, value: Any | None) -> Any | None:
        if value in self.empty_values:
            return None
        self.validate_no_null_characters(value)
        try: 
            key = self.to_field_name or "pk"
            if isinstance(value, self.queryset.model):
                value = getattr(value, key)
            value, created = self.queryset.get_or_create(**{key: value}, defaults=self.defaults)
            setattr(value, '_created_by_form', created)
        except (ValueError, TypeError, self.queryset.model.DoesNotExist):
            raise ValidationError(
                self.error_messages["invalid_choice"],
                code="invalid_choice",
                params={"value": value},
            )
        return value

class RecipeStepForm(ModelForm):
    class Meta:
        model = RecipeStep
        fields = '__all__'
    
    ingredient = AutoCreateModelField(Ingredient.objects.all(), to_field_name='name', widget=TextChoiceWidget(datalist_id='ingredient-list'), empty_label=None, required=False)

class BaseRecipeStepFormset(BaseInlineFormSet):
    def remove_temporary(self):
        for form in self.forms:
            object = form.cleaned_data.get('ingredient', None)
            if object and getattr(object, '_created_by_form', False):
                object.delete()
    
    def get_deletion_widget(self):
        return CheckboxInput(attrs={'class': 'visually-hidden'})

RecipeStepFormset = inlineformset_factory(
    parent_model=Recipe,
    model=RecipeStep,
    form=RecipeStepForm,
    formset=BaseRecipeStepFormset,
    fields='__all__')

