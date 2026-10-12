from typing import Any
from markdown.core import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from markdown.treeprocessors import Treeprocessor
from markdown.postprocessors import Postprocessor

import re

class InteractiveTasklistTreeprocessor(Treeprocessor):
    # Match "[x]2! "
    RE_CHECKBOX = re.compile(r'^ *\[(?P<state>[ xX]?)\](?:(?P<lineno>\d+)!)?(?= )')

    def get_checkbox_html(self, state: str, lineno: str = None, append_label=False):
        html = '<input type="checkbox"{active}{checked} />'.format(
            active=f' data-line={lineno}' if lineno else ' disabled',
            checked=' checked' if state.casefold() == 'x' else '')

        if append_label:
            html += '<label class="task-list-control" />'
        return html

    def get_checkbox(self, text, append_label=False) -> str | None:
        print(f"Trying checkbox on {text=}")
        m = self.RE_CHECKBOX.match(text)
        if m is None:
            return None
        
        return self.md.htmlStash.store(self.get_checkbox_html(
            m.group('state'), m.group('lineno'), append_label
        )) + ' ' + text[m.end():]

    def inline(self, li):
        """Search for checkbox directly in `li` tag."""

        placeholder = self.get_checkbox(li.text)
        if placeholder:
            li.text = placeholder
            return True
        return False

    def sub_paragraph(self, li):
        """Search for checkbox in sub-paragraph."""

        if len(li):
            first = next(iter(li))
            if first.tag == "p" and first.text is not None:
                placeholder = self.get_checkbox(first.text)
                if placeholder:
                    first.text = placeholder
                    return True
        return False

    def run(self, root):
        """Find list items that start with [ ] or [x] or [X]."""

        self.append_label = bool(self.config["append_label"])
        parent_map = {c: p for p in root.iter() for c in p}
        task_items = []
        lilinks = root.iter('li')
        for li in lilinks:
            if li.text is None or li.text == "":
                if not self.sub_paragraph(li):
                    continue
            elif not self.inline(li):
                continue

            # Checkbox found
            c = li.attrib.get("class", "")
            classes = [] if c == "" else c.split()
            classes.append("task-list-item")
            li.attrib["class"] = ' '.join(classes)
            task_items.append(li)

        for li in task_items:
            parent = parent_map[li]
            c = parent.attrib.get("class", "")
            classes = [] if c == "" else c.split()
            if "task-list" not in classes:
                classes.append("task-list")
            parent.attrib["class"] = ' '.join(classes)
        return root

class InteractiveTasklistPreprocessor(Preprocessor):
    RE = re.compile(r'\[[ xX]?\]')
    def run(self, lines: list[str]) -> list[str]:
        for i in range(len(lines)):
            lines[i] = self.RE.sub(rf'\g<0>{i + 1}!', lines[i])
        return lines

class InteractiveTasklistPostprocessor(Postprocessor):
    RE = re.compile(r'(\[[ xX]?\])\d+!')
    def run(self, text) -> Any:
        return self.RE.sub(r'\1', text)

class InteractiveTasklist(Extension):
    def __init__(self, *args, **kwargs):
        """Initialize."""

        self.config = {
            'append_label': [
                False,
                "Add an empty label tag after the input tag to allow for custom styling - Default: False"
            ],
        }

        super().__init__(*args, **kwargs)

    def extendMarkdown(self, md: Markdown):
        tasklist = InteractiveTasklistTreeprocessor(md)
        tasklist.config = self.getConfigs()

        line_annotator = InteractiveTasklistPreprocessor(md)
        line_deannotator = InteractiveTasklistPostprocessor(md)
        md.preprocessors.register(line_annotator, "task-list", 90)
        md.postprocessors.register(line_deannotator, "task-list", 10)
        md.treeprocessors.register(tasklist, "task-list", 25)
        md.registerExtension(self)
