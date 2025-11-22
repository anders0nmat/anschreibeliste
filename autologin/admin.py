from django.contrib import admin
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.forms import ModelForm, Select
from .models import AutoLogin, AutoLoginHistory
# Register your models here.

class HistoryInline(admin.TabularInline):
    model = AutoLoginHistory
    readonly_fields = [field.name for field in AutoLoginHistory._meta.fields]
    
def get_active_sessions() -> tuple[str, str]:
    return ((k, k) for k in Session.objects.filter(expire_date__gt=timezone.now()).values_list('session_key', flat=True))

class AutoLoginForm(ModelForm):
    class Meta:
        model = AutoLogin
        fields = '__all__'
        widgets = {
            'session_key': Select(choices=get_active_sessions)
        }

admin.site.register(AutoLogin, list_display=('name', 'user'), inlines=[HistoryInline], form=AutoLoginForm)
