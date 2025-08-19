from django.contrib import admin
from .models import AutoLogin
# Register your models here.

admin.site.register(AutoLogin, list_display=('device', 'user'))
