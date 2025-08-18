from typing import Any
from xml.etree.ElementTree import Element
from markdown.core import Markdown
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension

from urllib.parse import urlparse, urljoin

class BasePathTreeprocessor(Treeprocessor):
    def run(self, root: Element) -> Element | None:
        img_path = self.config['img_path']
        link_path = self.config['link_path']

        for element in root.iter('img'):
            url = urlparse(element.attrib['src'])
            if not url.netloc:
                # relative url
                element.attrib['src'] = url._replace(path=urljoin(img_path, url.path)).geturl()
        for element in root.iter('a'):
            url = urlparse(element.attrib['href'])
            if not url.netloc and url.path:
                # relative url
                element.attrib['href'] = url._replace(path=urljoin(link_path, url.path)).geturl()

class BasePath(Extension):
    def __init__(self, img_path: str = '', link_path: str = '', **kwargs: Any) -> None:
        self.config = {
            'img_path': [img_path, 'Base path to append to img elements with relative paths - Default: ""'],
            'link_path': [link_path, 'Base path to append to a elements with relative paths - Default: ""'],
        }

        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        processor = BasePathTreeprocessor(md)
        processor.config = self.getConfigs()
        md.treeprocessors.register(processor, 'base-path', 15)