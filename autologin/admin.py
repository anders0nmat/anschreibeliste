from django.contrib import admin
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.forms import ModelForm, Select
from .models import PrivilegedSession
# Register your models here.

def get_active_sessions() -> tuple[str, str]:
    return ((k, k) for k in Session.objects.filter(expire_date__gt=timezone.now()).values_list('session_key', flat=True))

class PrivilegedSessionForm(ModelForm):
    class Meta:
        model = PrivilegedSession
        fields = '__all__'
        widgets = {
            'session_key': Select(choices=get_active_sessions)
        }

@admin.register(PrivilegedSession)
class PrivilegedSessionForm(admin.ModelAdmin):
    list_display = ('name', 'session_key_prefix', 'last_changed')
    form = PrivilegedSessionForm
    
    class Media:
        css = {"all": ["autologin/autologin.css"]}
        
    @admin.display()
    def session_key_prefix(self, obj: PrivilegedSession) -> str:
        return obj.session_key[:5]
    

