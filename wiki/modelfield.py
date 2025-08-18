from django.db.models import BinaryField
from django.core.files.base import ContentFile, File
from django import forms

class BinaryFile(ContentFile):
    def __init__(self, content: bytes | str, url: str = None) -> None:
        super().__init__(content, url)
        self.url = url

    def __str__(self) -> str:
        return self.name or self.url or ''
 
class BinaryFileField(BinaryField):
    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault('editable', True)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if not self.editable:
            kwargs["editable"] = False
        else:
            del kwargs["editable"]
        return name, path, args, kwargs

    def get_prep_value(self, value):
        if isinstance(value, File):
            value = value.read()
        return value
    
    def from_db_value(self, value, expression, connection):
        return BinaryFile(value)
    
    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.FileField,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
