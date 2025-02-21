from django.db import models
from django.db.models import Window, F, Q, Value
from django.db.models.functions import Lag, Lead
from django.db.models.functions.datetime import Now
from typing import Optional, Union
from datetime import timedelta
from django.contrib.auth.models import User

class TransactionManager(models.Manager):
	def __init__(self, timejump_threshold: Union[timedelta, False]=False) -> None:
		super().__init__()
		self.default_timejump = timejump_threshold

	def recent(self, account=None, timejump: Union[timedelta, False, None]=None, user: Optional[User] = None):
		manager = self.filter(closing_balance=None).order_by('-timestamp')
		if account is not None:
			manager = manager.filter(account=account)
		can_revert_annotated = False
		if user is not None:
			if user.is_staff:
				manager = manager.annotate(allow_revert=Value(True))
			else:
				manager = manager.annotate(
					_timedelta_now=Now() - F('timestamp'))
				can_revert_annotated = True
		if timejump is None:
			timejump = self.default_timejump
		if timejump is not False:
			manager = manager.annotate(
				_previous_timestamp=Window(expression=Lag("timestamp", offset=1, default=None)),
				_timedelta_before=F("timestamp") - F("_previous_timestamp"),
				timejump_before=Q(_timedelta_before__gt=timejump),

				_next_timestamp=Window(expression=Lead("timestamp", offset=1, default=Now())),
				_timedelta_after=F("_next_timestamp") - F("timestamp"),
				timejump_after=Q(_timedelta_after__gt=timejump),
			)
			if can_revert_annotated:
				manager = manager.annotate(
					allow_revert=Q(issuer=user) and Q(_timedelta_now__lt=timejump))
				can_revert_annotated = False
		if can_revert_annotated:
			manager = manager.annotate(
				allow_revert=Q(issuer=user))
		
		return manager

class AccountManager(models.Manager):
	def grouped(self):
		return self.filter(active=True).order_by(F("group__order").asc(nulls_first=True), 'name')

class ProductManager(models.Manager):
	def grouped(self):
		return self.order_by(F("group__order").asc(nulls_first=True), 'order')
	
