from django.db import models
from django.utils.translation import gettext as _

# Create your models here.

class PrivilegedSession(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)
    session_key = models.CharField(max_length=100, primary_key=True)
    last_changed = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

