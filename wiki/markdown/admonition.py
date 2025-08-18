from typing import Any
from markdown.blockparser import BlockParser
from markdown.extensions.admonition import AdmonitionProcessor
from markdown import Extension
import copy
import re

from typing import TypedDict, Iterable

class AdmonitionDefinition(TypedDict):
    title_prefix: str
    default_title: str
    alias: Iterable[str]

class IconAdmonition(Extension):
    """ Custom Admonition extension for Python-Markdown. """
    def __init__(self, admonitions: dict[str, AdmonitionDefinition] = None, **kwargs: Any) -> None:
        if not admonitions:
            admonitions = {}
        self.config = {
            'admonitions': [copy.deepcopy(admonitions), 'List of admonition options. Default: {}'],
        }

        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        """ Add Admonition to Markdown instance. """
        config = self.getConfigs()
        md.parser.blockprocessors.register(CustomAdmonitionProcessor(
            admonitions=config['admonitions'],  parser=md.parser), 'icon-admonition', 106)

class CustomAdmonitionProcessor(AdmonitionProcessor):
    admonitions: dict[str, AdmonitionDefinition]
    aliases: dict[str, str]

    def __init__(self, admonitions: dict[str, AdmonitionDefinition], parser: BlockParser) -> None:
        self.admonitions = admonitions
        self.aliases = {}

        for key, item in self.admonitions.items():
            self.aliases[key] = key
            self.aliases.update((alias.lower(), key) for alias in item['alias'])

        super().__init__(parser)

    def get_class_and_title(self, match: re.Match[str]) -> tuple[str, str | None]:
        klass, title = match.group(1).lower(), match.group(2)
        klass = self.RE_SPACES.sub(' ', klass)
        klass = self.aliases.get(klass, klass)

        admonition = self.admonitions.get(klass, {})

        if title is None:
            # no title was provided, use the capitalized class name as title
            # e.g.: `!!! note` will render
            # `<p class="admonition-title">Note</p>`
            title = klass.split(' ', 1)[0].capitalize()
            title = admonition.get('default_title', title)
        elif title == '':
            # an explicit blank title should not be rendered
            # e.g.: `!!! warning ""` will *not* render `p` with a title
            title = None

        if title:
            title = admonition.get('title_prefix', '') + title

        return klass, title
