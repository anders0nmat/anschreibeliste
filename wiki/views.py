from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponseRedirect, FileResponse, HttpResponse,HttpResponseBadRequest, HttpResponseNotFound
from django.forms import modelform_factory, HiddenInput, inlineformset_factory, FileInput
from django.core.validators import validate_slug
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.forms import ModelForm
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from http import HTTPStatus
from itertools import islice
import re

from .models import Article, Attachment
from .markdown import render_markdown

# Create your views here.

class AttachmentForm(ModelForm):
    template_name = 'wiki/snippets/attachment_form.html'

class ArticleTree:
    slug: str | None
    title: str | None
    children: dict[str, "ArticleTree"]
    order: list[str]

    current: bool

    def __init__(self, slug: str | None, title: str | None = None) -> None:
        self.slug = slug
        self.title = title
        self.current = False
        self.children = {}
        self.order = []

    def __repr__(self) -> str:
        return f"ArticleTree(slug={self.slug}, title={self.title}, children={self.children})"

    @property
    def ordered_children(self) -> list["ArticleTree"]:
        return [self.children[key] for key in self.order]

    def add(self, slug: str, title: str):
        self._add(slug.split('_'), slug, title)

    def _add(self, path: list[str], slug: str, title: str):
        key, *rest = path

        if rest:
            # More to come
            if key not in self.children:
                self.children[key] = ArticleTree(slug=None)
                self.order.append(key)
            self.children[key]._add(rest, slug, title)
        else:
            # No more to come
            node = ArticleTree(slug, title)
            if key in self.children:
                node.children = self.children[key].children
                node.order = self.children[key].order
            else:
                self.order.append(key)
            self.children[key] = node

    def flatten(self):
        """
        Flatten Nodes with only one children
        """
        for child in self.children.values():
            child.flatten()

        keys = set(self.children.keys())
        for key in keys:
            child = self.children[key]
            if len(child.children) == 1 and not child.title:
                grandchild_key, grandchild = child.children.popitem()
                del self.children[key]
                new_key = f"{key}_{grandchild_key}"
                self.children[new_key] = grandchild
                # Replace old key with new one in self.order
                self.order = [new_key if e == key else e for e in self.order]

    def flatten_empty(self):
        """
        Merge nodes with key '' to parent
        """
        for child in self.children.values():
            child.flatten_empty()

        if '' in self.children:
            empty_child = self.children['']
            for key, child in empty_child.children.items():
                new_key = f"_{key}"
                self.children[new_key] = child
                self.order.append(new_key)
            if empty_child.title:
                empty_child.children.clear()
            else:
                del self.children['']
                self.order.remove('')

    def restrict_depth(self, depth: int):
        """
        Merge together nodes with a depth > `depth`
        """

        # To match "expected" and "logical" depth values
        MIN_DEPTH = 1

        for child in self.children.values():
            child.restrict_depth(max(depth - 1, MIN_DEPTH))
        
        if depth == MIN_DEPTH:
            # Need to merge with children
            keys = set(self.children.keys())
            for key in keys:
                # for each child
                for key2, child in self.children[key].children.items():
                    # take all descandants
                    new_key = f"{key}_{key2}"
                    self.children[new_key] = child
                    self.order.append(new_key)
                    # If a child is marked current, after the flattening,
                    # they are on the same level as their former parents, therefore,
                    # their parent should not be marked current
                    if child.current:
                        self.children[key].current = False
                # and delete the child (or its children)
                if self.children[key].title:
                    self.children[key].children.clear()
                else:
                    del self.children[key]
                    self.order.remove(key)         

    def fill_missing(self, prefix_slug: str = ''):
        """
        Fills missing `slug` and `title` information
        """
        if prefix_slug:
            prefix_slug += '_'
        for key, child in self.children.items():
            if not child.slug:
                child.slug = prefix_slug + key
            if not child.title:
                child.title = child.slug.replace('_', ' ').replace('-', ' ').title()
            child.fill_missing(prefix_slug=child.slug)

    def mark_current(self, slug: str):
        """
        sets `node.current` for all nodes along the given slug
        """
        keys = slug.split('_')
        node = self
        for key in keys:
            if key in node.children:
                node = node.children[key]
                node.current = True
            else:
                break


def get_article_tree(current_slug: str = None) -> list:
    """
    Groups articles by slug prefix
    """

    articles = Article.objects.exclude(slug='_start').values('slug', 'explicit_title', 'content_title')
    startpage_article = Article.objects.filter(slug='_start').first()
    root = ArticleTree('')
    if startpage_article:
        startpage_title = startpage_article.title
    else:
        # Translators: Default title of the wiki startpage
        startpage_title = _('Home')

    root.add('_start', startpage_title)
    for article in articles:
        root.add(article['slug'], article['explicit_title'] or article['content_title'])

    if current_slug:
        root.mark_current(current_slug)
    root.flatten()
    root.flatten_empty()
    root.restrict_depth(3)
    root.fill_missing()

    return root.ordered_children

def article_detail(request: HttpRequest, slug: str):
    # If article exists: display article
    # If article does not exist: Show error and allow for article to be created
    template = 'wiki/main.html' if slug == '_start' else 'wiki/article_detail.html'

    article = Article.objects.filter(slug=slug).first()
    return render(request, template, {
        'article_list': Article.objects.all(),
        'article_tree': get_article_tree(slug),
        'article': article,
        'slug': slug,
    })

def article_update(request: HttpRequest, slug: str = None):
    # If article exists: display edit article
    # If article does not exist: display create page
    ArticleForm = modelform_factory(Article, fields=['order', 'explicit_title', 'slug', 'raw_content'], widgets={
        'order': HiddenInput()
    })
    ArticleForm.base_fields['explicit_title'].widget.attrs['placeholder'] = _('(Optional)')
    ArticleForm.base_fields['slug'].widget.attrs['placeholder'] = _('(Optional)')
    ArticleForm.base_fields['raw_content'].widget.attrs['placeholder'] = _('(Markdown supported)')
    ArticleForm.base_fields['raw_content'].widget.attrs['cols'] = '20'


    AttachmentFormset = inlineformset_factory(Article, Attachment,
        fields=['name', 'content'],
        extra=1,
        form=AttachmentForm,
        widgets={
            'content': FileInput(),
        })

    article = Article.objects.filter(slug=slug).first()

    if request.method == "POST":
        form = ArticleForm(request.POST, instance=article, label_suffix='')
        formset = AttachmentFormset(request.POST, request.FILES, instance=article, form_kwargs={'label_suffix': ''})
        if form.is_valid() and formset.is_valid():
            article: Article = form.save()
            formset.instance = article
            formset.save()
            return HttpResponseRedirect(article.get_absolute_url())
    else:
        initial = None
        if not article:
            try:
                validate_slug(slug)
                initial = {'slug': slug}
            except ValidationError:
                pass
        form = ArticleForm(instance=article, initial=initial, label_suffix='')
        formset = AttachmentFormset(instance=article, form_kwargs={'label_suffix': ''})

    if slug:
        attachment_list = Attachment.objects.filter(article__slug=slug)
    else:
        attachment_list = None
    
    return render(request, 'wiki/article_update.html', {
        'article_list': Article.objects.all(),
        'article_tree': get_article_tree(slug),
        'attachment_list': attachment_list,
        'article': article,
        'form': form,
        'formset': formset,
    })

def article_attachment_list(request: HttpRequest, slug: str):
    files = Attachment.objects.filter(article__slug=slug)
    return render(request, 'wiki/article_files.html', {
        'file_list': files,
        'article_tree': get_article_tree(slug),
        'slug': slug,
    })

def article_attachment(request: HttpRequest, slug: str, name: str):
    attachment = get_object_or_404(Attachment, article__slug=slug, name=name)
    return FileResponse(attachment.content, as_attachment=False, filename=attachment.name)

@require_POST
def article_checkbox(request: HttpRequest, slug: str):
    article = get_object_or_404(Article, slug=slug)

    VALUE_MAP = {
        'true': True,
        'false': False,
        'on': True,
        'off': False,
        'yes': True,
        'no': False,
    }
    try:
        checkbox_index = int(request.POST.get('index'))
        checkbox_state = VALUE_MAP[request.POST.get('value', '').casefold()]
    except (KeyError, ValueError):
        return HttpResponseBadRequest("Requires 'index' and 'value' field in POST body")

    """
    RegEx Explaination:
    each checkbox line must:
    - start with any number of whitespace (space or tab) '[ \t]*'
    - A list item '[*+-]'
    - Followed by at least one space '[ \t]+'
    - Followed by a valid checkbox '\[([ xX])\]'
      - A valid checkbox is one of '[ ]', '[x]', '[X]'
      - We capture the string inside the square brackets for use later
    - Followed by at least a space (space or tab) '[ \t]' (We dont need any more, so one does fine)
    """
    matches = re.finditer(r'^[ \t]*[*+-][ \t]+\[([ xX])\][ \t]', article.content, re.MULTILINE)

    checkbox_match = next(islice(matches, checkbox_index, None), None)
    if not checkbox_match:
        return HttpResponseNotFound(f'No checkbox with id {checkbox_index} in article {article.slug}')
    
    new_state = 'x' if checkbox_state else ' '
    article.content = article.content[:checkbox_match.start(1)] + new_state + article.content[checkbox_match.end(1):]

    article.save()
    
    return HttpResponse(status=HTTPStatus.NO_CONTENT)

@csrf_exempt
@require_POST
def article_preview(request: HttpRequest):
    return HttpResponse(render_markdown(request.body.decode()))

