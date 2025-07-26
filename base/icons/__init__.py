from django import template
from django.utils.safestring import mark_safe
from django.conf import settings
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from pathlib import Path
from functools import lru_cache

register = template.Library()

default_class = "lucide"

@lru_cache(maxsize=0 if settings.DEBUG else 128)
def get_icon(name: str) -> ET.Element:
    module_dir = Path(__file__).parent

    path = module_dir / f"{name}.svg"
    if path.is_file():
        root = ET.parse(path).getroot()
        for node in root.iter():
            node.tag = node.tag.removeprefix('{http://www.w3.org/2000/svg}')
        return root

    with ZipFile(module_dir / "icons.zip") as archive:
        try:
            with archive.open(f"{name}.svg") as file:
                root = ET.parse(file).getroot()
                for node in root.iter():
                    node.tag = node.tag.removeprefix('{http://www.w3.org/2000/svg}')
                return root
        except KeyError:
            raise ValueError(f"Icon '{name}' not found")

@register.simple_tag
def icon(name: str, size: int = None, **kwargs):
    icon = get_icon(name)
    if size:
        kwargs.setdefault("width", str(size))
        kwargs.setdefault("height", str(size))
    if default_class:
        before = kwargs.get('class')
        before = (' ' + before) if before else ''
        kwargs['class'] = default_class + before
    icon.attrib.update({key.replace('_', '-'): value for key, value in kwargs.items()})

    return mark_safe(ET.tostring(icon, encoding="unicode", method="html"))

