from typing import Any, Collection, Self

from django.db import models
from django.utils.translation import gettext as _
from django.utils.text import slugify
from django.urls import reverse, NoReverseMatch

from .markdown import render_markdown, AnalyzeMarkdownParser
from .modelfield import BinaryFileField, File

# Create your models here.

class Article(models.Model):
    explicit_title = models.CharField(verbose_name=_("title"), max_length=255, default='', blank=True)
    slug = models.SlugField(verbose_name=_('slug'), db_index=False, unique=True, blank=True)
    raw_content = models.TextField(_('content'))

    order = models.PositiveIntegerField(
        verbose_name=_('order'),
        default=0,
        blank=False,
        null=False,
        db_index=True
    )

    _content_modified: bool

    content_title = models.CharField(max_length=255, editable=False)
    content_html = models.TextField(editable=False)

    class Meta:
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")
        ordering = ['order']

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._content_modified = False

    def __str__(self) -> str:
        return self.title
    
    @property
    def title(self) -> str:
        return self.explicit_title or self.content_title
    
    @title.setter
    def title(self, value) -> str:
        self.explicit_title = value

    @property
    def content(self) -> str:
        return self.raw_content
    
    @content.setter
    def content(self, value):
        self.raw_content = value
        self._content_modified = True

    def clean(self) -> None:
        self._content_modified = True
        return super().clean()

    def save(self, **kwargs) -> None:
        update_fields = set(kwargs.get("update_fields", (field.name for field in self._meta.get_fields())))
        
        if "raw_content" in update_fields and self._content_modified:
            update_fields |= self.render_markdown()

        if not self.slug:
            self.slug = slugify(self.title)
            update_fields.add('slug')

        if "update_fields" in kwargs:
            kwargs["update_fields"] = update_fields

        return super().save(**kwargs)
    
    def render_markdown(self) -> set[str]:
        """
        Returns: Set of modified fields
        """
        self.content_html = render_markdown(self.content, image_base_path='files/')
        self._content_modified = False

        parser = AnalyzeMarkdownParser()
        parser.feed(self.content_html)

        # fit as many words as possible without reaching MAX_TITLE_LENGTH
        MAX_TITLE_LENGTH = 50
        self.content_title = ''
        for word in parser.title.split():
            space = ' ' if self.content_title else ''
            if len(self.content_title) + len(space) + len(word) > MAX_TITLE_LENGTH:
                break
            self.content_title += space + word

        # If the first word is already too long, just live with it
        if not self.content_title:
            self.content_title = parser.title[:MAX_TITLE_LENGTH]

        return {'content_html', 'content_title'}
    
    def get_absolute_url(self):
        if not self.slug:
            return reverse("wiki:main")
        return reverse("wiki:article_detail", kwargs={"slug": self.slug})

class Attachment(models.Model):
    article = models.ForeignKey(Article, verbose_name=_('article'), on_delete=models.CASCADE)
    name = models.CharField(verbose_name=_('name'), max_length=50, blank=True)
    content = BinaryFileField(verbose_name=_('content'), default=b'')
    content: File

    class Meta:
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")
        unique_together = ('article', 'name')

    def __str__(self) -> str:
        return f"{self.article.slug}/{self.name}"

    @classmethod
    def from_db(cls: type[Self], db: str | None, field_names: Collection[str], values: Collection[Any]) -> Self:
        instance = super().from_db(db, field_names, values)

        if instance.content is not models.DEFERRED:
            try:
                instance.content.url = reverse('wiki:article_attachment', kwargs={
                    'slug': instance.article.slug,
                    'name': instance.name
                })
            except NoReverseMatch:
                pass
        return instance

    def save(self, **kwargs) -> None:
        if not self.name:
            self.name = self.content.name

        super().save(**kwargs)
