from typing import Any
from xml.etree.ElementTree import Element, SubElement
from markdown.core import Markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

from urllib.parse import urlparse, urljoin

class AdaptiveImages(Extension):
    def __init__(self, light_suffix: str = '-light', dark_suffix: str = '-dark', **kwargs: Any) -> None:
        self.config = {
            'light_suffix': [light_suffix, 'The suffix to use for light-mode images. Default: "-light"'],
            'dark_suffix': [dark_suffix, 'The suffix to use for dark-mode images. Default: "-dark"'],
        }

        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        config = self.getConfigs()
        md.treeprocessors.register(AdaptiveImageTreeprocessor(
            light_suffix=config['light_suffix'],
            dark_suffix=config['dark_suffix']), 'adaptive-image', 14)
        
class AdaptiveImageTreeprocessor(Treeprocessor):
    light_suffix: str
    dark_suffix: str

    def __init__(self, light_suffix: str, dark_suffix: str, **kwargs) -> None:
        self.light_suffix = light_suffix
        self.dark_suffix = dark_suffix
        super().__init__(**kwargs)

    def run(self, root: Element) -> Element | None:
        # list() because modifying tree during iter is undefined behavior
        for element in list(root.iter('img')):
            url = urlparse(element.attrib['src'])
            if url.netloc: continue
            if url.fragment not in ('adaptive',): continue

            # './asd/filename.png' -> ['.', 'asd', 'filename.png'][-1] -> ['filename', 'png'][0]
            filename, extension = url.path.rsplit('/', 1)[-1].rsplit('.', 1)
            light_mode = not filename.endswith(self.dark_suffix)
            
            if light_mode:
                new_filename = filename.removesuffix(self.light_suffix) + self.dark_suffix
            else:
                new_filename = filename.removesuffix(self.dark_suffix) + self.light_suffix
            new_filename += '.' + extension
            new_url = url._replace(fragment="", path=urljoin(url.path, new_filename)).geturl()

            element.tag = 'picture'
            SubElement(element, 'source', {
                'srcset': new_url,
                'media': f'(prefers-color-scheme: {"dark" if light_mode else "light"})',
            })
            SubElement(element, 'img', element.attrib | {
                'src': url._replace(fragment="").geturl(),
            })
            element.attrib.clear()
            


            

