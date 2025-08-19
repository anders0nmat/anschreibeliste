from typing import Type
from django.db import models
from django.contrib.auth import get_user_model, models as auth_models
from django.utils.translation import gettext as _

# Create your models here.

UserModel: Type[auth_models.AbstractBaseUser] = get_user_model()

class AutoLogin(models.Model):
    user = models.ForeignKey(UserModel, verbose_name=_('User'), on_delete=models.CASCADE)
    device = models.GenericIPAddressField()
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('user', 'device'), name='unique_autologin_rules')
        ]
        
    def __str__(self) -> str:
        return f"{self.device} ({self.user})"
