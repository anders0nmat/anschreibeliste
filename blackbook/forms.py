
from typing import Any, Callable, Iterator, Tuple
from django.forms import ModelForm, ModelChoiceField, FileField, ValidationError
from itertools import groupby
from io import BytesIO
from ledger.models import Product
from .models import Recipe, ServingGlass, PrepMethod
from django.utils.translation import gettext_lazy as _

import xml.etree.ElementTree as ET

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

class RecipeForm(ModelForm):
    class Meta:
        model = Recipe
        fields = '__all__'
    
    product = GroupedModelChoiceField(Product.objects.filter(category=Product.ProductCategory.ARTICLE), group_by_field='group', group_label=lambda group: group.name, label=_('product'), required=False)

class ServingGlassForm(ModelForm):
    class Meta:
        model = ServingGlass
        fields = '__all__'
    
    icon_file = FileField(required=False, label="Icon from file")
    
    def clean_icon(self):
        if 'icon_file' in self.files:
            data = self.files['icon_file']
            if data.content_type == 'image/svg+xml':
                new_data = BytesIO()
                for chunk in data.chunks():
                    new_data.write(chunk)
                new_data.seek(0)
                element = ET.parse(new_data).getroot()
            else:
                raise ValidationError('Unknown mime type', 'invalid_mime_type')
        else:
            data = self.cleaned_data['icon']
            try:
                element = ET.fromstring(data)
            except:
                raise ValidationError('Invalid SVG code', 'invalid_svg')
        
        # Remove all <script> tags
        for script_tag in element.iter('script'):
            element.remove(script_tag)

        # Remove all svg namespace
        for node in element.iter():
            node.tag = node.tag.removeprefix('{http://www.w3.org/2000/svg}')

        return ET.tostring(element, encoding="unicode", method="html", xml_declaration=False)

class PrepMethodForm(ModelForm):
    class Meta:
        model = PrepMethod
        fields = '__all__'
    
    icon_file = FileField(required=False, label="Icon from file")
    
    def clean_icon(self):
        if 'icon_file' in self.files:
            data = self.files['icon_file']
            if data.content_type == 'image/svg+xml':
                new_data = BytesIO()
                for chunk in data.chunks():
                    new_data.write(chunk)
                new_data.seek(0)
                element = ET.parse(new_data).getroot()
            else:
                raise ValidationError('Unknown mime type', 'invalid_mime_type')
        else:
            data = self.cleaned_data['icon']
            try:
                element = ET.fromstring(data)
            except:
                raise ValidationError('Invalid SVG code', 'invalid_svg')
        
        # Remove all <script> tags
        for script_tag in element.iter('script'):
            element.remove(script_tag)

        # Remove all svg namespace
        for node in element.iter():
            node.tag = node.tag.removeprefix('{http://www.w3.org/2000/svg}')

        return ET.tostring(element, encoding="unicode", method="html", xml_declaration=False)
