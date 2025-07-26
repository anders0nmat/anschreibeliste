from django.contrib import admin

from .models import AutoLogin

admin.site.register(AutoLogin, list_display=('device','user'))

