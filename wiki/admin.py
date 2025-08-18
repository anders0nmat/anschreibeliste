from django.contrib import admin
from django import forms
from adminsortable2.admin import SortableAdminMixin

from . import models
from .modelfield import BinaryFileField

# Register your models here.

class AdminFileWidget(forms.ClearableFileInput):
    template_name = "admin/widgets/clearable_file_input.html"

@admin.register(models.Article)
class ArticleAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["order", "title", "slug"]

admin.site.register(models.Attachment, list_display=['article', 'name'], formfield_overrides={
    BinaryFileField: {'widget': AdminFileWidget},
})
