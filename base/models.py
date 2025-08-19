from typing import Type
from django.contrib.auth import get_user_model, models as auth_models

UserModel: Type[auth_models.AbstractBaseUser] = get_user_model()

class ProjectUser(UserModel):
    class Meta:
        proxy = True
        default_permissions = []
        permissions = [
            ("view_transactions", "Can view Transactions")
		]
