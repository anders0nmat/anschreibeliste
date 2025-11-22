from typing import Type
from django.db import models
from django.contrib.auth import get_user_model, models as auth_models
from django.utils.translation import gettext as _

# Create your models here.

UserModel: Type[auth_models.AbstractBaseUser] = get_user_model()

class AutoLogin(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)
    user = models.ForeignKey(UserModel, verbose_name=_('User'), on_delete=models.CASCADE)
    session_key = models.CharField(max_length=100)

    history: models.QuerySet["AutoLoginHistory"]
        
    def __str__(self) -> str:
        return f"{self.user}"
    
class AutoLoginHistory(models.Model):
    login = models.ForeignKey(AutoLogin, on_delete=models.CASCADE, related_name='history')
    timestamp = models.DateTimeField(auto_now_add=True)
    new_session_id = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=1024)
    

