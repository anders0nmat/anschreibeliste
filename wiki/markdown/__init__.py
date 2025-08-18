
from markdown import markdown

from .base_path import BasePath
from .admonition import IconAdmonition

from pymdownx.emoji import to_alt

from base.icons import icon
from html.parser import HTMLParser

from django.urls import reverse
from django.utils.translation import pgettext

def render_markdown(content: str, image_base_path='') -> str:
    link_base_path = reverse('wiki:main')
    return markdown(content, extensions=[
            BasePath(img_path=image_base_path, link_path=link_base_path),
            IconAdmonition({
                'info': {
                    'title_prefix': icon('info'),
                    'default_title': pgettext('admonition title', 'Info'),
                    'alias': ['note', 'information', 'hint'],
                },
                'tip': {
                    'title_prefix': icon('lightbulb'),
                    'default_title': pgettext('admonition title', 'Tip'),
                    'alias': [],
                },
                'important': {
                    'title_prefix': icon('message-square-warning'),
                    'default_title': pgettext('admonition title', 'Important'),
                    'alias': [],
                },
                'warning': {
                    'title_prefix': icon('triangle-alert'),
                    'default_title': pgettext('admonition title', 'Warning'),
                    'alias': ['warn'],
                },
                'caution': {
                    'title_prefix': icon('octagon-alert'),
                    'default_title': pgettext('admonition title', 'Caution'),
                    'alias': ['danger'],
                },
            }),
            'pymdownx.superfences',
            'pymdownx.highlight',
            'pymdownx.saneheaders',
            'sane_lists',
            'footnotes',
            'tables',
            'pymdownx.mark',
            'pymdownx.emoji',
            'pymdownx.escapeall',
            'pymdownx.tilde',
            'pymdownx.tasklist',
            'pymdownx.smartsymbols',
        ], extension_configs={
            'pymdownx.highlight': {
                'auto_title': True,
                'auto_title_map': {
                    'Text Only': 'Text',
                }
            },
            'pymdownx.escapeall': {
                'hardbreak': True,
                'nbsp': True,
            },
            'pymdownx.tilde': {
                'subscript': False,
            },
            'pymdownx.smartsymbols': {
                'care_of': False,
                'ordinal_numbers': False,
            },
            'pymdownx.emoji': {
                'emoji_generator': to_alt
            },
            'footnotes': {
                'BACKLINK_TEXT': icon('move-up'),
            }
        })

class AnalyzeMarkdownParser(HTMLParser):
    HEADINGS = tuple(f'h{level}' for level in range(1, 7))

    _heading_depth: int
    _element_depth: int
    _first_heading_content: str
    _first_element_content: str

    def __init__(self, *, convert_charrefs: bool = True) -> None:
        self._heading_depth = 0
        self._element_depth = 0
        self._first_element_content = ''
        self._first_heading_content = ''
        super().__init__(convert_charrefs=convert_charrefs)

    @property
    def title(self) -> str:
        """
        The first heading encoutered (h1 to h6).
        If no heading present, the content of the first element encoutered.
        """
        return self._first_heading_content or self._first_element_content

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.HEADINGS and self._heading_depth > -1:
            self._heading_depth += 1
        
        if tag not in self.HEADINGS and self._element_depth > -1:
            self._element_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self.HEADINGS and self._heading_depth > 0:
            self._heading_depth -= 1
            if self._heading_depth == 0:
                self._heading_depth = -1
        
        if tag not in self.HEADINGS and self._element_depth > 0:
            self._element_depth -= 1
            if self._element_depth == 0:
                self._element_depth = -1

    def handle_data(self, data: str) -> None:
        if self._heading_depth > 0:
            self._first_heading_content += data
        if self._element_depth > 0:
            self._first_element_content += data

